from __future__ import annotations

import json
from pathlib import PurePosixPath

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models import Citation, MigrationStrategy
from app.providers.base import ModelProvider, ProviderUnavailable


class RepositoryEvidence(BaseModel):
    repo_url: HttpUrl
    dependency_manifests: list[str] = Field(max_length=8)
    python_files: list[str] = Field(max_length=200)
    symbol_matches: list[str] = Field(max_length=200)
    baseline_summary: str = Field(max_length=2_000)

    @property
    def known_files(self) -> set[str]:
        return set(self.dependency_manifests) | set(self.python_files)

    def prompt_payload(self) -> str:
        return json.dumps(self.model_dump(mode="json"), separators=(",", ":"))


class StrategyPlan(BaseModel):
    strategies: list[MigrationStrategy] = Field(min_length=3, max_length=3)


class MigrationPlanner:
    def __init__(self, provider: ModelProvider, *, repair_attempts: int = 1) -> None:
        self._provider = provider
        self._repair_attempts = repair_attempts

    async def plan(
        self, evidence: RepositoryEvidence, citations: list[Citation]
    ) -> list[MigrationStrategy]:
        if not citations:
            raise ProviderUnavailable("Migration planning requires retained official citations")
        system = (
            "You are BranchShift's migration planner. Return exactly three distinct strategies "
            "with ids minimal, compatibility, and refactor. Use only target_files listed in the "
            "repository evidence and only source_urls listed in official_sources. Do not include "
            "commands, prose outside the schema, secrets, or new file paths."
        )
        user = self._user_prompt(evidence, citations)
        last_error = ""
        for attempt in range(self._repair_attempts + 1):
            if attempt:
                user += (
                    "\nYour previous response failed validation. Correct it without expanding "
                    f"scope. Validation issue: {last_error[:500]}"
                )
            response = await self._provider.complete_json(
                system=system,
                user=user,
                schema=StrategyPlan,
            )
            try:
                return self._validate(response.strategies, evidence, citations)
            except ValueError as exc:
                last_error = str(exc)
        raise ProviderUnavailable(f"Nemotron strategy validation failed: {last_error}")

    @staticmethod
    def _user_prompt(evidence: RepositoryEvidence, citations: list[Citation]) -> str:
        sources = [
            {
                "title": item.title,
                "url": str(item.url),
                "evidence": item.evidence,
            }
            for item in citations
        ]
        return (
            "repository_evidence="
            + evidence.prompt_payload()
            + "\nofficial_sources="
            + json.dumps(sources, separators=(",", ":"))
        )

    @staticmethod
    def _validate(
        strategies: list[MigrationStrategy],
        evidence: RepositoryEvidence,
        citations: list[Citation],
    ) -> list[MigrationStrategy]:
        expected_ids = {"minimal", "compatibility", "refactor"}
        actual_ids = {item.id for item in strategies}
        if actual_ids != expected_ids:
            raise ValueError("strategy ids must be minimal, compatibility, and refactor")
        rationales = {" ".join(item.rationale.lower().split()) for item in strategies}
        if len(rationales) != 3:
            raise ValueError("strategies must have distinct rationales")

        allowed_urls = {str(item.url) for item in citations}
        known_files = evidence.known_files
        for strategy in strategies:
            if not strategy.ordered_steps or len(strategy.ordered_steps) > 8:
                raise ValueError(f"{strategy.id} must contain between 1 and 8 ordered steps")
            if not strategy.source_urls:
                raise ValueError(f"{strategy.id} must cite retained official evidence")
            if any(str(url) not in allowed_urls for url in strategy.source_urls):
                raise ValueError(f"{strategy.id} cites a source outside the retained evidence")
            if not strategy.target_files:
                raise ValueError(f"{strategy.id} must identify at least one target file")
            for target in strategy.target_files:
                normalized = PurePosixPath(target).as_posix()
                if normalized.startswith("../") or normalized.startswith("/"):
                    raise ValueError(f"{strategy.id} contains an unsafe target path")
                if normalized not in known_files:
                    raise ValueError(f"{strategy.id} references unknown file: {target}")
        return strategies
