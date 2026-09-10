from unittest.mock import AsyncMock

import httpx
import pytest

from app.orchestrator.research import MigrationResearch
from app.providers.base import ProviderUnavailable
from app.providers.tavily import (
    CANONICAL_MIGRATION_URL,
    MAX_GUIDE_BYTES,
    MAX_GUIDE_EXCERPT_CHARS,
    TavilyResearchProvider,
    extract_migration_citations,
    is_current_official_source,
)

HTML = '''<html><head><title>Official migration reference</title></head><body>
<nav>Navigation noise</nav><script>never retain script text</script><main><h1>Migration guide</h1>
<h2 id="validators">Changes to validators</h2><p>Actual validator section from fetched HTML.</p>
<h2 id="config">Changes to config</h2><p>Actual configuration section from fetched HTML.</p>
<h2 id="base">Changes to pydantic.BaseModel</h2><p>Actual model section from fetched HTML.</p>
</main></body></html>'''


def provider(response=None, error=None, handler=None):
    if handler is None:
        def handler(request):
            return httpx.Response(503)
    instance = TavilyResearchProvider("private-search-key", transport=httpx.MockTransport(handler))
    instance._client.search = AsyncMock(return_value=response or {"results": []}, side_effect=error)
    return instance


async def test_default_query_keeps_valid_search_when_canonical_fetch_is_unavailable():
    instance = provider({"results": [{
        "url": CANONICAL_MIGRATION_URL,
        "title": "Current official migration guide", "content": "Retained actual search excerpt",
    }]})
    result = await MigrationResearch(instance).collect()
    assert len(result) == 1
    assert str(result[0].url) == CANONICAL_MIGRATION_URL
    assert result[0].evidence == "Retained actual search excerpt"
    request = instance._client.search.await_args.kwargs
    assert request["query"] == "Pydantic v1 to v2 migration validators config parsing serialization"
    assert "pydantic.dev" in request["include_domains"]


async def test_search_is_enriched_with_actual_canonical_sections():
    instance = provider({"results": [{
        "url": CANONICAL_MIGRATION_URL,
        "title": "Migration guide", "content": "A short search snippet",
    }]}, handler=lambda request: httpx.Response(200, text=HTML))
    result = await MigrationResearch(instance).collect()
    assert len(result) == 4
    assert all("from fetched HTML" in item.evidence for item in result[:3])
    assert result[3].evidence == "A short search snippet"


@pytest.mark.parametrize("search_error", [None, RuntimeError("private-search-key must not leak")])
async def test_empty_or_failed_search_fetches_actual_public_guide_without_credentials(search_error):
    calls = []

    def fetch(request):
        calls.append(request)
        assert request.url == CANONICAL_MIGRATION_URL
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        assert "private-search-key" not in str(request.headers)
        return httpx.Response(200, text=HTML, headers={"Content-Type": "text/html"})

    result = await MigrationResearch(provider(error=search_error, handler=fetch)).collect()
    assert len(calls) == 1
    assert len(result) == 3
    assert all("from fetched HTML" in item.evidence for item in result)
    assert all(len(item.evidence) <= MAX_GUIDE_EXCERPT_CHARS for item in result)
    assert {str(item.url).split("#")[-1] for item in result} == {"validators", "config", "base"}


async def test_outdated_and_article_only_search_uses_canonical_fallback():
    urls = ["https://pydantic.dev/articles/pydantic-v2-alpha",
            "https://docs.pydantic.dev/2.3/migration/",
            "https://docs.pydantic.dev/1.10/blog/pydantic-v2-alpha/"]
    instance = provider(
        {"results": [{"url": url, "content": "old experimental source"} for url in urls]},
        handler=lambda request: httpx.Response(200, text=HTML),
    )
    result = await instance.search_official("Pydantic migration")
    assert all(str(item.url).startswith(CANONICAL_MIGRATION_URL) for item in result)


async def test_external_redirect_is_rejected_before_following_it():
    requests = []

    def fetch(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://evil.example/docs/"})

    with pytest.raises(ProviderUnavailable, match="redirected outside"):
        await provider(handler=fetch).search_official("Pydantic migration")
    assert len(requests) == 1


async def test_known_official_redirect_is_followed_and_final_url_is_cited():
    calls = []
    redirected = "https://docs.pydantic.dev/latest/migration/"

    def fetch(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(302, headers={"Location": redirected})
        return httpx.Response(200, text=HTML)

    result = await provider(handler=fetch).search_official("Pydantic migration")
    assert calls == [CANONICAL_MIGRATION_URL, redirected]
    assert str(result[0].url).startswith(redirected)


async def test_both_failures_are_reported_without_exposing_search_secret():
    instance = provider(
        error=RuntimeError("private-search-key"), handler=lambda request: httpx.Response(503),
    )
    with pytest.raises(ProviderUnavailable) as caught:
        await instance.search_official("Pydantic migration")
    assert "Tavily search failed (RuntimeError)" in str(caught.value)
    assert "HTTP 503" in str(caught.value)
    assert "private-search-key" not in str(caught.value)


async def test_oversized_public_guide_is_rejected():
    instance = provider(handler=lambda request: httpx.Response(
        200, content=b"x" * (MAX_GUIDE_BYTES + 1)
    ))
    with pytest.raises(ProviderUnavailable, match="size limit"):
        await instance.search_official("Pydantic migration")


@pytest.mark.parametrize("url", [
    "https://pydantic.dev/articles/news/", "https://pydantic.dev/docs/validation/2.3/migration/",
    "https://docs.pydantic.dev/2.3/migration/", "https://pydantic.dev:444/docs/validation/latest/",
    "http://pydantic.dev/docs/validation/latest/", "https://evil.example/docs/validation/latest/",
])
def test_official_allowlist_excludes_other_content_and_old_versions(url):
    assert not is_current_official_source(url)


def test_html_extraction_excludes_navigation_and_scripts():
    result = extract_migration_citations(HTML, CANONICAL_MIGRATION_URL)
    assert all("Navigation noise" not in item.evidence for item in result)
    assert all("script text" not in item.evidence for item in result)


async def test_migration_excerpt_retains_later_signature_and_config_guidance():
    # Both real official sections put these migration rules after character 1,500.
    introduction = "Earlier migration guidance. " * 60
    html = (
        '<main><h2 id="validators">Changes to validators</h2><p>'
        + introduction
        + "A model validator can receive an instance of the model.</p>"
        + '<h2 id="config">Changes to config</h2><p>'
        + introduction
        + "allow_population_by_field_name is renamed to populate_by_name.</p></main>"
    )
    instance = provider(handler=lambda request: httpx.Response(200, text=html))
    result = await MigrationResearch(instance).collect()
    assert "instance of the model" in result[0].evidence
    assert "populate_by_name" in result[1].evidence
    assert all(len(item.evidence) <= MAX_GUIDE_EXCERPT_CHARS for item in result)
