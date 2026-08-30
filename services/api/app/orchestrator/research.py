from __future__ import annotations

from urllib.parse import urlparse

from app.domain.models import Citation
from app.providers.base import ProviderUnavailable, ResearchProvider

ALLOWED_RESEARCH_HOSTS = {
    "docs.pydantic.dev",
    "docs.python.org",
    "packaging.python.org",
}


class MigrationResearch:
    def __init__(self, provider: ResearchProvider) -> None:
        self._provider = provider

    async def collect(self) -> list[Citation]:
        raw = await self._provider.search_official(
            "Pydantic v1 to v2 migration validators config parsing serialization",
            max_results=5,
        )
        retained: list[Citation] = []
        seen: set[str] = set()
        for citation in raw:
            url = str(citation.url)
            host = (urlparse(url).hostname or "").lower()
            if host not in ALLOWED_RESEARCH_HOSTS or url in seen:
                continue
            retained.append(
                Citation(
                    title=citation.title.strip()[:200],
                    url=citation.url,
                    evidence=" ".join(citation.evidence.split())[:500],
                )
            )
            seen.add(url)
        if not retained:
            raise ProviderUnavailable("No allowlisted official migration evidence was returned")
        if not any(urlparse(str(item.url)).hostname == "docs.pydantic.dev" for item in retained):
            raise ProviderUnavailable(
                "The research set does not include official Pydantic guidance"
            )
        return retained
