import asyncio
import base64
import json
import shlex
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.domain.models import BranchStatus, CreateRunRequest, MigrationStrategy, RunStatus
from app.orchestrator import run_manager
from app.orchestrator.baseline import BaselineOutcome
from app.orchestrator.behavior_probes import (
    PROBE_MARKER,
    BehaviorProbeSuite,
    probe_suite_digest,
)
from app.orchestrator.branch_runner import FileReplacement, PatchProposal
from app.orchestrator.planner import RepositoryEvidence
from app.orchestrator.run_manager import RunManager
from app.providers.base import CommandResult, SandboxState
from app.storage.repositories import RunRepository


@pytest.mark.parametrize("scenario", [
    "disabled", "difference", "baseline_error", "branch_error", "probe_timeout",
    "truncated", "redacted", "cancelled", "revalidation_failed",
])
async def test_behavior_review_is_separate_retained_evidence_and_never_a_test_gate(
    tmp_path, monkeypatch, scenario,
):
    database_url = f"sqlite:///{tmp_path / 'behavior-workflow.db'}"
    repository = RunRepository(database_url)
    monkeypatch.setattr(run_manager, "source_provenance", lambda: {})
    settings = Settings(
        mode="live", database_url=database_url, nebius_api_key="synthetic-key",
        nebius_project_id="synthetic-project", tavily_api_key="synthetic-research",
    )
    manager = RunManager(repository, settings)
    declared = BehaviorProbeSuite.model_validate({"cases": [{
        "id": "numeric-name", "module": "sample_app.models", "model": "User",
        "payload": {"name": 123, "label": "probe-only-unique-key"},
    }]})
    contract = "c" * 64
    baseline = BaselineOutcome(
        state=SandboxState("original-baseline"),
        evidence=RepositoryEvidence(
            repo_url="https://github.com/owner/repo", dependency_manifests=["pyproject.toml"],
            python_files=["src/app/models.py"], symbol_matches=["src/app/models.py:1:validator"],
            baseline_summary="1 passed", baseline_tests_collected=1,
            test_contract_digest=contract, test_outcomes={"test_models::test_name": "passed"},
            file_contents={"src/app/models.py": "from pydantic import validator\n"},
        ),
        commit_sha="d" * 40, tests_collected=1, tests_passed=1,
    )
    strategies = [MigrationStrategy(
        id=name, title=name.title(), rationale=f"Synthetic {name} strategy",
        ordered_steps=["Update validator"],
        source_urls=["https://docs.pydantic.dev/latest/migration/"],
        target_files=["src/app/models.py"],
    ) for name in ("minimal", "compatibility", "refactor")]
    monkeypatch.setattr(run_manager.BaselineRunner, "prepare", AsyncMock(return_value=baseline))
    monkeypatch.setattr(run_manager.MigrationResearch, "collect", AsyncMock(return_value=[]))

    async def plan(_self, evidence, citations):
        assert evidence is baseline.evidence
        assert "probe-only-unique-key" not in evidence.prompt_payload()
        return strategies

    monkeypatch.setattr(run_manager.MigrationPlanner, "plan", plan)
    monkeypatch.setattr(run_manager, "TavilyResearchProvider", lambda *_: object())
    validation_parents, probe_parents, frozen_inputs, model_prompts = [], [], [], []
    final_probe_started = asyncio.Event()

    class SyntheticModel:
        usage = {"requests": 0}

        async def complete_json(self, *, system, user, schema):
            assert "probe-only-unique-key" not in system + user
            assert "behavior_probes" not in user
            model_prompts.append(user)
            return PatchProposal(replacements=[FileReplacement(
                path="src/app/models.py", lines=["from pydantic import field_validator"],
            )], summary="Synthetic proposal")

    class SyntheticSandbox:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def run(self, parent, command, *, timeout_seconds):
            if PROBE_MARKER in command:
                probe_parents.append(parent.checkpoint_id)
                assert timeout_seconds == 30
                assert command.startswith("cd /workspace/repo/project && .venv/bin/python")
                frozen_inputs.append(json.loads(base64.b64decode(shlex.split(command)[-1])))
                assert frozen_inputs[-1] == declared.model_dump(mode="json")
                original = parent.checkpoint_id == "original-baseline"
                if scenario == "baseline_error" and original or (
                    scenario == "branch_error" and not original
                ):
                    raise RuntimeError("/private/sensitive-path raw-secret")
                if scenario == "probe_timeout":
                    raise TimeoutError("remote timeout raw-secret")
                if scenario == "cancelled" and parent.checkpoint_id == "validated-4":
                    final_probe_started.set()
                    await asyncio.Event().wait()
                observation = (
                    {"id": "numeric-name", "status": "accepted", "value": {"name": "123"}}
                    if original else
                    {"id": "numeric-name", "status": "rejected", "error_type": "ValidationError"}
                )
                output = PROBE_MARKER + json.dumps({
                    "suite_digest": probe_suite_digest(declared), "observations": [observation],
                })
                if scenario == "truncated":
                    output = output[:75]
                elif scenario == "redacted":
                    output = PROBE_MARKER + json.dumps({
                        "suite_digest": probe_suite_digest(declared), "observations": [{
                            "id": "numeric-name", "status": "accepted",
                            "value": {"name": "[REDACTED]"},
                        }],
                    })
                return CommandResult(
                    state=SandboxState(f"discarded-probe-child-{len(probe_parents)}"),
                    stdout=output, stderr="", exit_code=0, elapsed_seconds=0.01,
                )
            validation_parents.append(parent)
            checkpoint_id = f"validated-{len(validation_parents)}"
            await asyncio.sleep(0)
            markers = {
                "TEST_EXIT": 0, "PIP_EXIT": 0, "RUFF_EXIT": 0,
                "TESTS_COLLECTED": 1, "TESTS_PASSED": 1, "TESTS_FAILED": 0,
                "TESTS_SKIPPED": 0, "TEST_OUTCOMES_PRESERVED": 1,
                "PYDANTIC_MAJOR": 2, "INSTALL_EXIT": 0,
                "CONTRACT_BEFORE": contract, "CONTRACT_AFTER": contract,
            }
            if scenario == "revalidation_failed" and checkpoint_id == "validated-4":
                markers.update(TEST_EXIT=1, TESTS_PASSED=0, TESTS_FAILED=1,
                               TEST_OUTCOMES_PRESERVED=0)
            return CommandResult(
                state=SandboxState(checkpoint_id),
                stdout="\n".join(f"__BRANCHSHIFT_{key}={value}" for key, value in markers.items()),
                stderr="", exit_code=0, elapsed_seconds=0.01,
            )

    monkeypatch.setattr(run_manager, "NebiusModelProvider", lambda *a, **kw: SyntheticModel())
    monkeypatch.setattr(run_manager, "ContreeSandboxProvider", lambda *a, **kw: SyntheticSandbox())
    created = await manager.create(CreateRunRequest(
        repo_url="https://github.com/owner/repo", project_path="project",
        behavior_probes=None if scenario == "disabled" else declared,
    ))
    if scenario == "cancelled":
        await asyncio.wait_for(final_probe_started.wait(), timeout=2)
        await manager.shutdown()
    else:
        await asyncio.wait_for(manager.wait(created.id), timeout=3)
        await manager.shutdown()
    repository.close()

    reopened = RunRepository(database_url)
    try:
        summary = await reopened.require_run(created.id)
        assert summary.status is (
            RunStatus.CANCELLED if scenario == "cancelled" else
            RunStatus.FAILED if scenario == "revalidation_failed" else RunStatus.COMPLETED
        )
        assert validation_parents == [baseline.state] * 4
        assert len(model_prompts) == 3
        assert summary.baseline_checkpoint_id == "original-baseline"
        assert {b.checkpoint_id for b in summary.branches} == {
            "validated-1", "validated-2", "validated-3",
        }
        assert all(b.status is BranchStatus.PASSED for b in summary.branches)
        assert summary.revalidation is not None
        assert summary.revalidation.checkpoint_id == "validated-4"
        assert summary.revalidated_checkpoint_id == "validated-4"
        assert "raw-secret" not in summary.model_dump_json()
        if scenario == "disabled":
            assert probe_parents == []
            assert summary.behavior_probes is None and summary.baseline_probe_results is None
            assert summary.baseline_probe_error is None
            assert all(b.behavior_probe_results is None for b in summary.branches)
            return
        assert summary.behavior_probes == declared
        assert len(probe_parents) == 5
        assert set(probe_parents) == {"original-baseline", *(f"validated-{i}" for i in range(1, 5))}
        assert len(frozen_inputs) == 5
        branch_records = [*summary.branches, summary.revalidation]
        if scenario in {"probe_timeout", "truncated", "redacted", "baseline_error"}:
            assert summary.baseline_probe_results is None and summary.baseline_probe_error
            assert all(b.behavior_probe_comparison is None for b in branch_records)
            assert all(b.behavior_probe_error for b in branch_records)
        elif scenario == "branch_error":
            assert summary.baseline_probe_results is not None
            assert all(b.behavior_probe_results is None for b in branch_records)
            assert all(b.behavior_probe_comparison is None for b in branch_records)
            assert all(b.behavior_probe_error for b in branch_records)
        else:
            assert summary.baseline_probe_results.observations[0].status == "accepted"
            assert summary.baseline_probe_error is None
            for branch in summary.branches:
                assert branch.behavior_probe_results.observations[0].status == "rejected"
                assert branch.behavior_probe_comparison.review_only is True
                assert branch.behavior_probe_comparison.cases[0].status == "different"
                assert branch.behavior_probe_error is None
            if scenario == "cancelled":
                # Cancellation is propagated; the prior verification is still durable.
                assert summary.revalidation.behavior_probe_results is None
                assert summary.revalidation.status is BranchStatus.PASSED
                assert summary.winner_id is None and summary.patch is None
            else:
                assert summary.revalidation.behavior_probe_comparison.cases[0].status == "different"
                if scenario == "difference":
                    assert summary.winner_id is not None and summary.patch is not None
                    from app.reports import render_markdown_report

                    report = render_markdown_report(summary, [])
                    assert "## Explicit behavior review" in report
                    assert "different: acceptance" in report
                    assert "not a migration acceptance gate" in report
                    assert "accepted:" in report and "rejected: ValidationError" in report
                else:
                    assert summary.revalidation.status is BranchStatus.FAILED
                    assert summary.winner_id is None and summary.patch is None
    finally:
        reopened.close()
