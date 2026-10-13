from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from tavily import AsyncTavilyClient  # type: ignore[import-untyped]

from app.domain.models import Citation, http_url
from app.providers.base import ProviderUnavailable

OFFICIAL_DOMAINS = {
    "docs.pydantic.dev", "pydantic.dev", "docs.python.org", "packaging.python.org",
}
CANONICAL_MIGRATION_URL = "https://pydantic.dev/docs/validation/latest/get-started/migration/"
MAX_GUIDE_BYTES = 2_000_000
MAX_GUIDE_EXCERPT_CHARS = 3_000


def is_pydantic_documentation_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    if "/articles/" in path or "/blog/" in path or "alpha" in path:
        return False
    return (
        parsed.hostname == "docs.pydantic.dev" and path.startswith("/latest/")
    ) or (
        parsed.hostname == "pydantic.dev" and path.startswith("/docs/validation/latest/")
    )


def is_current_official_source(url: str) -> bool:
    parsed = urlparse(url)
    try:
        safe_port = parsed.port in {None, 443}
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or not safe_port:
        return False
    if parsed.hostname in {"docs.pydantic.dev", "pydantic.dev"}:
        return is_pydantic_documentation_url(url)
    return parsed.hostname in {"docs.python.org", "packaging.python.org"}


@dataclass
class _Section:
    title: str
    anchor: str
    text: list[str] = field(default_factory=list)


class _GuideParser(HTMLParser):
    """Extract actual visible sections and heading anchors, excluding navigation and scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[_Section] = []
        self.scoped_sections: list[_Section] = []
        self._scope = 0
        self._ignored: list[str] = []
        self._heading: str | None = None
        self._anchor = ""
        self._heading_parts: list[str] = []
        self._in_title = False
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "aside", "header", "footer", "button"}:
            self._ignored.append(tag)
        if self._ignored:
            return
        if tag in {"main", "article"}:
            self._scope += 1
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "h3", "h4"}:
            self._heading = tag
            self._anchor = dict(attrs).get("id") or ""
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._ignored:
            if tag == self._ignored[-1]:
                self._ignored.pop()
            return
        if tag == "title":
            self._in_title = False
        if tag == self._heading:
            section = _Section(" ".join(self._heading_parts).strip(), self._anchor)
            self.sections.append(section)
            if self._scope:
                self.scoped_sections.append(section)
            self._heading = None
        if tag in {"main", "article"}:
            self._scope = max(0, self._scope - 1)

    def handle_data(self, data: str) -> None:
        if self._ignored or not data.strip():
            return
        text = " ".join(data.split())
        if self._in_title:
            self.title.append(text)
        elif self._heading:
            self._heading_parts.append(text)
        elif self.sections:
            self.sections[-1].text.append(text)


def extract_migration_citations(html: str, url: str) -> list[Citation]:
    parser = _GuideParser()
    parser.feed(html)
    sections = parser.scoped_sections or parser.sections
    selected: list[_Section] = []
    for term in ("validator", "config", "basemodel"):
        candidates = [
            item for item in sections
            if term in item.title.lower().replace(" ", "") and item.text
        ]
        if candidates:
            selected.append(max(candidates, key=lambda item: len(" ".join(item.text))))
    if not selected:
        selected = [item for item in sections if item.text][:1]
    if not selected:
        raise ProviderUnavailable("Official migration guide returned no usable article text")
    page_title = " ".join(parser.title).strip() or sections[0].title or url
    citations: list[Citation] = []
    seen: set[str] = set()
    for section in selected:
        source_url = url + "#" + section.anchor if section.anchor else url
        if source_url in seen:
            continue
        seen.add(source_url)
        citations.append(Citation(
            title=(section.title if section.anchor else page_title)[:200],
            url=http_url(source_url),
            evidence=" ".join([section.title, *section.text])[:MAX_GUIDE_EXCERPT_CHARS],
        ))
    return citations


class TavilyResearchProvider:
    def __init__(
        self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ProviderUnavailable("TAVILY_API_KEY is not configured")
        self._client = AsyncTavilyClient(api_key=api_key)
        self._transport = transport

    async def search_official(self, query: str, *, max_results: int = 5) -> list[Citation]:
        limit = min(5, max(1, max_results))
        search_failure = "Tavily returned no usable current Pydantic documentation"
        citations: list[Citation] = []
        try:
            response = await asyncio.wait_for(self._client.search(
                query=query, max_results=limit, include_domains=sorted(OFFICIAL_DOMAINS),
                search_depth="advanced",
            ), timeout=15.0)
            seen: set[str] = set()
            for result in response.get("results", []):
                url = str(result.get("url", ""))
                content = " ".join(str(result.get("content", "")).split())[:1_500]
                if not is_current_official_source(url) or not content or url in seen:
                    continue
                seen.add(url)
                citations.append(Citation(
                    title=str(result.get("title", url))[:200],
                    url=http_url(url), evidence=content,
                ))
        except Exception as exc:  # noqa: BLE001 - fall back to a bounded public document fetch
            search_failure = f"Tavily search failed ({type(exc).__name__})"
        try:
            fallback = await asyncio.wait_for(self._fetch_migration_guide(), timeout=20.0)
        except (ProviderUnavailable, httpx.HTTPError, TimeoutError) as exc:
            if any(is_pydantic_documentation_url(str(item.url)) for item in citations):
                return citations[:limit]
            detail = str(exc) if isinstance(exc, ProviderUnavailable) else type(exc).__name__
            raise ProviderUnavailable(
                f"{search_failure}; direct official migration guide unavailable: {detail}"
            ) from exc
        return [*fallback, *citations][:limit]

    async def _fetch_migration_guide(self) -> list[Citation]:
        url = CANONICAL_MIGRATION_URL
        # This separate public client never receives Tavily credentials or authenticated cookies.
        async with httpx.AsyncClient(
            transport=self._transport, timeout=10.0, follow_redirects=False, trust_env=False,
            headers={"Accept": "text/html"},
        ) as client:
            for _redirect in range(4):
                if not is_pydantic_documentation_url(url) or not is_current_official_source(url):
                    raise ProviderUnavailable(
                        "Official guide redirected outside current Pydantic docs"
                    )
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ProviderUnavailable("Official guide returned an invalid redirect")
                        url = urljoin(url, location)
                        continue
                    if response.status_code != 200:
                        raise ProviderUnavailable(
                            f"Official guide returned HTTP {response.status_code}"
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_GUIDE_BYTES:
                            raise ProviderUnavailable(
                                "Official guide exceeded the download size limit"
                            )
                    return extract_migration_citations(body.decode("utf-8", errors="replace"), url)
        raise ProviderUnavailable("Official guide exceeded the redirect limit")
