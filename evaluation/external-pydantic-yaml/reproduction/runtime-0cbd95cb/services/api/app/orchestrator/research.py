from __future__ import annotations

from app.domain.models import Citation
from app.providers.base import ProviderUnavailable, ResearchProvider
from app.providers.tavily import (
    MAX_GUIDE_EXCERPT_CHARS,
    is_current_official_source,
    is_pydantic_documentation_url,
)


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
            if not is_current_official_source(url) or url in seen:
                continue
            retained.append(
                Citation(
                    title=citation.title.strip()[:200],
                    url=citation.url,
                    evidence=" ".join(citation.evidence.split())[:MAX_GUIDE_EXCERPT_CHARS],
                )
            )
            seen.add(url)
        if not retained:
            raise ProviderUnavailable("No allowlisted official migration evidence was returned")
        if not any(is_pydantic_documentation_url(str(item.url)) for item in retained):
            raise ProviderUnavailable(
                "The research set does not include official Pydantic guidance"
            )
        return retained
