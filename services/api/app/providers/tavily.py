from __future__ import annotations

from urllib.parse import urlparse

from tavily import AsyncTavilyClient  # type: ignore[import-untyped]

from app.domain.models import Citation, http_url
from app.providers.base import ProviderUnavailable

OFFICIAL_DOMAINS = {
    "docs.pydantic.dev",
    "docs.python.org",
    "packaging.python.org",
}


class TavilyResearchProvider:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderUnavailable("TAVILY_API_KEY is not configured")
        self._client = AsyncTavilyClient(api_key=api_key)

    async def search_official(self, query: str, *, max_results: int = 5) -> list[Citation]:
        response = await self._client.search(
            query=query,
            max_results=max_results,
            include_domains=sorted(OFFICIAL_DOMAINS),
            search_depth="advanced",
        )
        citations: list[Citation] = []
        for result in response.get("results", []):
            url = str(result.get("url", ""))
            if urlparse(url).hostname not in OFFICIAL_DOMAINS:
                continue
            content = " ".join(str(result.get("content", "")).split())[:360]
            citations.append(
                Citation(
                    title=str(result.get("title", url)),
                    url=http_url(url),
                    evidence=content,
                )
            )
        return citations
