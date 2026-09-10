from collections.abc import Sequence
from typing import Any

import pytest

from app.domain.models import Citation, MigrationStrategy, http_url
from app.orchestrator.planner import (
    MigrationPlanner,
    RepositoryEvidence,
    StrategyPlan,
    evidence_plan_schema,
)
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
    assert issubclass(provider.calls[0]["schema"], StrategyPlan)
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


async def test_planner_rejects_test_edits_even_for_known_files(evidence, citations):
    invalid = valid_plan()
    invalid.strategies[0].target_files = ["tests/test_models.py"]
    with pytest.raises(ProviderUnavailable, match="protected test"):
        await MigrationPlanner(FakeModelProvider([invalid]), repair_attempts=0).plan(
            evidence, citations
        )


async def test_planner_receives_exact_retained_source(evidence, citations):
    evidence.file_contents = {
        "src/app/models.py": "from pydantic import validator\nclass User: pass\n",
        "pyproject.toml": '[project]\ndependencies=["pydantic<2"]\n',
    }
    plan = valid_plan()
    for item in plan.strategies:
        item.target_files.append("pyproject.toml")
    provider = FakeModelProvider([plan])
    await MigrationPlanner(provider).plan(evidence, citations)
    assert "class User: pass" in provider.calls[0]["user"]
    assert 'pydantic<2' in provider.calls[0]["user"]


def test_strategy_schema_requires_nonempty_target_files():
    from pydantic import ValidationError

    schema = MigrationStrategy.model_json_schema()
    assert "target_files" in schema["required"]
    assert schema["properties"]["target_files"]["minItems"] == 1
    payload = valid_plan().strategies[0].model_dump()
    del payload["target_files"]
    with pytest.raises(ValidationError, match="target_files"):
        MigrationStrategy.model_validate(payload)


async def test_strategy_cannot_omit_pydantic_dependency_manifest(evidence, citations):
    evidence.file_contents = {
        "pyproject.toml": 'dependencies=["pydantic<2"]', "src/app/models.py": "class User: pass"
    }
    with pytest.raises(ProviderUnavailable, match="dependency manifests"):
        await MigrationPlanner(FakeModelProvider([valid_plan()]), repair_attempts=0).plan(
            evidence, citations
        )


def test_source_evidence_rejects_oversized_file(evidence):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="oversized file"):
        RepositoryEvidence.model_validate({
            **evidence.model_dump(),
            "file_contents": {"src/app/models.py": "x" * 25_001},
        })


def test_request_schema_enumerates_only_retained_files_and_sources(evidence, citations):
    evidence.python_files.append("src/app/not_retained.py")
    evidence.file_contents = {
        "pyproject.toml": "[project]\n",
        "src/app/models.py": "class User: pass\n",
        "tests/test_models.py": "def test_user(): pass\n",
    }
    schema = evidence_plan_schema(evidence, citations).model_json_schema()
    strategy_ref = schema["properties"]["strategies"]["items"]["$ref"].split("/")[-1]
    fields = schema["$defs"][strategy_ref]["properties"]
    assert fields["target_files"]["items"]["enum"] == ["pyproject.toml", "src/app/models.py"]
    assert fields["source_urls"]["items"]["enum"] == [str(SOURCE)]


@pytest.mark.parametrize(
    "field, invalid",
    [("target_files", ["src/app/invented_compat.py"]),
     ("source_urls", ["https://example.com/invented"])],
)
def test_enum_constraints_validate_raw_output(evidence, citations, field, invalid):
    from pydantic import ValidationError

    schema = evidence_plan_schema(evidence, citations)
    payload = valid_plan().model_dump(mode="json")
    payload["strategies"][0][field] = invalid
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_postvalidation_still_rejects_unknown_paths_independently(evidence, citations):
    invalid = valid_plan()
    invalid.strategies[0].target_files = ["invented.py"]
    with pytest.raises(ValueError, match="unknown file"):
        MigrationPlanner._validate(invalid.strategies, evidence, citations)


async def test_provider_schema_rejection_gets_one_bounded_repair(evidence, citations):
    class SchemaRejectingProvider(FakeModelProvider):
        async def complete_json(self, *, system, user, schema):
            if not self.calls:
                self.calls.append({"system": system, "user": user, "schema": schema})
                raise ProviderUnavailable("Model returned invalid structured content")
            return await super().complete_json(system=system, user=user, schema=schema)

    provider = SchemaRejectingProvider([valid_plan()])
    result = await MigrationPlanner(provider).plan(evidence, citations)
    assert len(result) == 3
    assert len(provider.calls) == 2
    assert "allowed enums" in provider.calls[1]["user"]
