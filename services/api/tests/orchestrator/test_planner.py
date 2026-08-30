from collections.abc import Sequence
from typing import Any

import pytest

from app.domain.models import Citation, MigrationStrategy, http_url
from app.orchestrator.planner import MigrationPlanner, RepositoryEvidence, StrategyPlan
from app.providers.base import ProviderUnavailable

SOURCE = http_url("https://docs.pydantic.dev/latest/migration/")


def strategy(strategy_id: str, rationale: str, target: str = "src/app/models.py"):
    return MigrationStrategy(
        id=strategy_id,
        title=strategy_id.title(),
        rationale=rationale,
        ordered_steps=["Update the validated model API", "Run the existing tests"],
        source_urls=[SOURCE],
        target_files=[target],
    )


def valid_plan() -> StrategyPlan:
    return StrategyPlan(
        strategies=[
            strategy("minimal", "Change only removed APIs"),
            strategy("compatibility", "Introduce a temporary v1 bridge"),
            strategy("refactor", "Adopt the complete v2 model style"),
        ]
    )


class FakeModelProvider:
    def __init__(self, responses: Sequence[StrategyPlan]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def complete_json(self, *, system: str, user: str, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return self.responses.pop(0)


@pytest.fixture
def evidence():
    return RepositoryEvidence(
        repo_url="https://github.com/owner/repo",
        dependency_manifests=["pyproject.toml"],
        python_files=["src/app/models.py", "tests/test_models.py"],
        symbol_matches=["src/app/models.py:12:@validator"],
        baseline_summary="13 tests collected; 13 passed",
    )


@pytest.fixture
def citations():
    return [Citation(title="Pydantic migration", url=SOURCE, evidence="Official mappings")]


async def test_planner_accepts_three_grounded_strategies(evidence, citations):
    provider = FakeModelProvider([valid_plan()])
    result = await MigrationPlanner(provider).plan(evidence, citations)
    assert [item.id for item in result] == ["minimal", "compatibility", "refactor"]
    assert provider.calls[0]["schema"] is StrategyPlan
    assert "src/app/models.py" in provider.calls[0]["user"]


async def test_planner_retries_once_after_unknown_file(evidence, citations):
    invalid = valid_plan()
    invalid.strategies[0].target_files = ["invented.py"]
    provider = FakeModelProvider([invalid, valid_plan()])
    result = await MigrationPlanner(provider).plan(evidence, citations)
    assert result[0].target_files == ["src/app/models.py"]
    assert len(provider.calls) == 2
    assert "unknown file" in provider.calls[1]["user"]


async def test_planner_fails_closed_after_retry_exhaustion(evidence, citations):
    invalid = valid_plan()
    invalid.strategies[0].source_urls = [http_url("https://example.com/untrusted")]
    provider = FakeModelProvider([invalid, invalid])
    with pytest.raises(ProviderUnavailable, match="outside the retained evidence"):
        await MigrationPlanner(provider).plan(evidence, citations)
