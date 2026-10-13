"""Replay immutable model artifacts as data, never import or execute upstream code."""

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.models import BranchStatus, Citation
from app.orchestrator.branch_runner import (
    BranchRunner,
    EditProposal,
    PatchProposal,
    evidence_patch_schema,
)
from app.orchestrator.planner import MigrationPlanner, RepositoryEvidence, StrategyPlan
from app.providers.base import SandboxState

DATA = Path(__file__).resolve().parents[4] / "evaluation/external-pydantic-yaml"
EVIDENCE_SHA = "5f881e2f0c3eb2448e96465e8fb4c3d10e4465b9bcc3f4427953156da8ea1d53"
PLAN_SHA = "5b2f7116f410b7add9ae38ebdc70d1840f79a774904091cb920159fdae4fdbf0"
CITATIONS_SHA = "66cfbb04e83ca2c28e8f41e5646fd404c40a3abbdd6575a1a4bc0fd9f442ae91"
ARTIFACT_SHA256 = {
    **{
        f"{session}/{name}": digest
        for session in ("line-edit-session", "schema-fixed-session")
        for name, digest in (
            ("repository-evidence.json", EVIDENCE_SHA),
            ("plan/result.json", PLAN_SHA),
            ("citations.json", CITATIONS_SHA),
        )
    },
    "line-edit-session/minimal/model-01/response.json":
        "efa9382cbb124529d6d6508733f1b0e7f80a6cf72d1f2a4cfb1f42d06d8e4b2a",
    "line-edit-session/minimal/model-02/response.json":
        "03827ac96cc5270595c1f352178a6377eaaf38b7ff54b5b2b9c8df8c98ea5773",
    "line-edit-session/refactor/model-01/response.json":
        "a795d5fb3989756051dd6554d4c4eaa9a0bdd64a50baff0c3f11abf3177ac5c3",
    "line-edit-session/refactor/model-02/response.json":
        "57c1c5357cce9bcf7cdde0913f107e608842fd1a43336b43f8340185d33fdbb1",
    "schema-fixed-session/minimal/model-01/response.json":
        "05edce5e7472bc54d22271c50ee9991b9626bb5f0254d77129562e4a26ee186e",
    "schema-fixed-session/compatibility/model-01/response.json":
        "5063fdf7dd68e50d4292c92cf5cdce10ecce5e3862ddd409da91739cb22a5622",
    "schema-fixed-session/refactor/model-01/response.json":
        "9b7ca10f23cf76bb2c35c3aa7807d4d45992726ef1fe61d16f1c41d63b689995",
    "schema-fixed-session/refactor/model-02/response.json":
        "ae99f7334d1d97ee6a9f80d35c7cd8a4a718f76a42ad3827581ac7a273819eaf",
}


def artifact(relative):
    raw = (DATA / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256[relative]
    return json.loads(raw)


def inputs(session, strategy_id):
    evidence = RepositoryEvidence.model_validate(artifact(f"{session}/repository-evidence.json"))
    plan = StrategyPlan.model_validate(artifact(f"{session}/plan/result.json"))
    strategy = next(item for item in plan.strategies if item.id == strategy_id)
    assert evidence.baseline_tests_collected == 15
    assert evidence.baseline_tests_passed == 14
    return strategy, evidence


class ArtifactModel:
    """Serve recorded outputs locally; legacy objects use the explicit historical replay path."""

    def __init__(self, paths):
        self.records = [artifact(path)["response"] for path in paths]
        self.requests = []

    async def complete_json(self, *, system, user, schema):
        self.requests.append(json.loads(user))
        assert set(schema.model_json_schema()["properties"]) == {"edits", "summary"}
        payload = self.records.pop(0)
        model = EditProposal if "edits" in payload else PatchProposal
        return model.model_validate(payload)


class NeverExecute:
    def __init__(self):
        self.calls = 0

    async def run(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("A rejected recorded proposal must never start an executor")


def assert_not_executed(result, executor):
    assert executor.calls == 0
    assert result.status is BranchStatus.FAILED
    # These are unobserved tests, not a completed suite with 0 of 15 passing.
    assert (result.tests_collected, result.tests_passed, result.tests_failed) == (0, 0, 0)
    assert result.test_exit_code is None
    assert result.pip_exit_code is None
    assert result.pydantic_major is None
    assert result.checkpoint_id is None
    assert result.test_outcomes_preserved is None
    assert result.elapsed_seconds == 0
    assert result.patch is None
    assert result.patch_applicable is False
    assert "No safe applicable patch" in result.failure_reason


@pytest.mark.parametrize("session,strategy_id,attempt,diagnostic", [
    ("line-edit-session", "minimal", "01", "overlap or share a start boundary"),
    ("line-edit-session", "minimal", "02", "total edit size limit"),
    ("line-edit-session", "refactor", "01", "total edit size limit"),
    ("line-edit-session", "refactor", "02", "invalid Python"),
    ("schema-fixed-session", "minimal", "01", "u0022u0022u0022"),
    ("schema-fixed-session", "compatibility", "01", "invalid Python"),
    ("schema-fixed-session", "refactor", "01", "u0022u0022u0022"),
    ("schema-fixed-session", "refactor", "02", "u0022u0022u0022"),
])
async def test_complete_recorded_bad_candidate_never_starts_executor(
    session, strategy_id, attempt, diagnostic,
):
    strategy, evidence = inputs(session, strategy_id)
    model = ArtifactModel([f"{session}/{strategy_id}/model-{attempt}/response.json"])
    executor = NeverExecute()
    result = await BranchRunner(model, executor, max_attempts=1).run(
        SandboxState("offline-baseline"), strategy, evidence
    )
    assert_not_executed(result, executor)
    assert len(model.requests) == 1
    assert diagnostic in result.diagnostics


def test_recorded_minimal_has_33_identical_same_boundary_edits():
    edits = artifact("line-edit-session/minimal/model-01/response.json")["response"]["edits"]
    ranges = Counter((item["path"], item["start_line"], item["end_line"]) for item in edits)
    repeated = ("src/pydantic_yaml/mixin.py", 182, 219)
    assert len(edits) == 40
    assert ranges[repeated] == 33
    assert edits[7:] == [edits[7]] * 33
    assert sum(len(item["lines"]) for item in edits) == 361


@pytest.mark.parametrize("strategy_id,total_lines,total_bytes", [
    ("minimal", 705, 20_096),
    ("refactor", 834, 33_238),
])
def test_recorded_aggregate_budget_overflow_is_not_an_individual_edit_overflow(
    strategy_id, total_lines, total_bytes,
):
    attempt = "02" if strategy_id == "minimal" else "01"
    edits = artifact(f"line-edit-session/{strategy_id}/model-{attempt}/response.json")[
        "response"
    ]["edits"]
    assert len(edits) <= 40
    assert max(len(item["lines"]) for item in edits) == 120
    assert sum(len(item["lines"]) for item in edits) == total_lines > 600
    assert sum(len(line.encode()) + 1 for item in edits for line in item["lines"]) == total_bytes
    # Minimal isolates the line budget; refactor exceeds both the line and byte budgets.
    assert (total_bytes > 24_000) is (strategy_id == "refactor")


def test_recorded_120_line_replacement_is_incomplete_even_in_isolated_python_ast():
    response = artifact("line-edit-session/refactor/model-02/response.json")["response"]
    assert len(response["edits"]) == 1
    edit = response["edits"][0]
    assert (edit["path"], edit["start_line"], edit["end_line"]) == (
        "src/pydantic_yaml/mixin.py", 1, 274
    )
    assert len(edit["lines"]) == 120
    assert edit["lines"][-1] == "        exclude_unset: bool = False,`, "
    # ast.parse only parses text. No upstream module imports or project code execution.
    with pytest.raises(SyntaxError):
        ast.parse("\n".join(edit["lines"]) + "\n", filename=edit["path"])


@pytest.mark.parametrize("strategy_id,first_error,last_error", [
    ("minimal", "overlap or share a start boundary", "total edit size limit"),
    ("refactor", "total edit size limit", "invalid Python"),
])
async def test_recorded_retry_sequence_retains_failures_and_original_baseline(
    strategy_id, first_error, last_error,
):
    strategy, evidence = inputs("line-edit-session", strategy_id)
    model = ArtifactModel([
        f"line-edit-session/{strategy_id}/model-{attempt}/response.json"
        for attempt in ("01", "02")
    ])
    executor = NeverExecute()
    result = await BranchRunner(model, executor, max_attempts=2).run(
        SandboxState("offline-baseline"), strategy, evidence
    )
    assert_not_executed(result, executor)
    assert len(model.requests) == 2
    assert first_error in model.requests[1]["previous_attempt"]
    assert last_error in result.diagnostics
    assert model.requests[0]["original_files"] == model.requests[1]["original_files"]
    assert "2 attempts" in result.failure_reason


def test_retained_legacy_response_cannot_be_decoded_as_active_edit_protocol():
    strategy, evidence = inputs("schema-fixed-session", "minimal")
    response = artifact("schema-fixed-session/minimal/model-01/response.json")["response"]
    with pytest.raises(ValidationError):
        evidence_patch_schema(strategy, evidence).model_validate(response)


def test_actual_saved_plan_is_rejected_for_undeclared_shim_path():
    session = "schema-fixed-session"
    plan = StrategyPlan.model_validate(artifact(f"{session}/plan/result.json"))
    evidence = RepositoryEvidence.model_validate(artifact(f"{session}/repository-evidence.json"))
    citations = [Citation.model_validate(item) for item in artifact(f"{session}/citations.json")]
    compatibility = next(item for item in plan.strategies if item.id == "compatibility")
    unsupported = "src/pydantic_yaml/compat/pydantic_shim.py"
    assert f"Create {unsupported}" in compatibility.ordered_steps[1]
    assert unsupported not in compatibility.target_files
    assert unsupported not in evidence.file_contents
    with pytest.raises(ValueError) as caught:
        MigrationPlanner._validate(plan.strategies, evidence, citations)
    assert str(caught.value) == (
        f"compatibility step references undeclared Python path: {unsupported}; "
        "use only retained editable target_files in ordered_steps"
    )
