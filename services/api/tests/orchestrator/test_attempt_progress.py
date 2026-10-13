import asyncio
import json
from collections import defaultdict
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.domain.events import EVENTS
from app.domain.models import CreateRunRequest, MigrationStrategy, RunStatus
from app.main import create_app
from app.orchestrator import run_manager
from app.orchestrator.baseline import BaselineOutcome
from app.orchestrator.branch_runner import FileReplacement, PatchProposal
from app.orchestrator.planner import RepositoryEvidence
from app.orchestrator.run_manager import RunManager
from app.providers.base import CommandResult, SandboxState
from app.storage.repositories import RunRepository


@pytest.mark.parametrize("outcome", ["completed", "cancelled", "revalidation_failed"])
async def test_manager_persists_per_branch_attempt_starts_before_model_calls(
    tmp_path, monkeypatch, outcome,
):
    cancel_during_proposal = outcome == "cancelled"
    database_url = f"sqlite:///{tmp_path / 'attempt-events.db'}"
    repository = RunRepository(database_url)
    provenance = {
        "orchestrator_revision": "a" * 40,
        "orchestrator_digest": "b" * 64,
        "orchestrator_dirty": True,
    }
    monkeypatch.setattr(run_manager, "source_provenance", lambda: provenance)
    settings = Settings(
        mode="live", database_url=database_url,
        nebius_api_key="synthetic-key", nebius_project_id="synthetic-project",
        tavily_api_key="synthetic-research", max_repository_bytes=123_456,
    )
    manager = RunManager(repository, settings)
    contract = "c" * 64
    baseline = BaselineOutcome(
        state=SandboxState(checkpoint_id="synthetic-baseline"),
        evidence=RepositoryEvidence(
            repo_url="https://github.com/owner/repo",
            dependency_manifests=["pyproject.toml"],
            python_files=["src/app/models.py"],
            symbol_matches=["src/app/models.py:1:validator"],
            baseline_summary="1 passed", baseline_tests_collected=1,
            test_contract_digest=contract,
            file_contents={"src/app/models.py": "from pydantic import validator\n"},
        ),
        commit_sha="d" * 40, tests_collected=1, tests_passed=1,
    )
    strategies = [MigrationStrategy(
        id=branch_id, title=branch_id.title(), rationale="Synthetic test strategy",
        ordered_steps=["Update validator"],
        source_urls=["https://docs.pydantic.dev/latest/migration/"],
        target_files=["src/app/models.py"],
    ) for branch_id in ("minimal", "compatibility", "refactor")]
    async def prepare(runner, *args, **kwargs):
        assert runner._max_repository_bytes == settings.max_repository_bytes
        assert kwargs["baseline_ref"] == "d" * 40
        return baseline

    monkeypatch.setattr(run_manager.BaselineRunner, "prepare", prepare)
    monkeypatch.setattr(run_manager.MigrationResearch, "collect", AsyncMock(return_value=[]))
    monkeypatch.setattr(run_manager.MigrationPlanner, "plan", AsyncMock(return_value=strategies))
    monkeypatch.setattr(run_manager, "TavilyResearchProvider", lambda *_: object())
    model_started = asyncio.Event()
    model_calls = defaultdict(int)
    parents = []

    class ObservedModel:
        usage = {"requests": 0}

        async def complete_json(self, *, system, user, schema):
            branch_id = json.loads(user)["strategy"]["id"]
            model_calls[branch_id] += 1
            events = await repository.list_events(created.id)
            progress = [event for event in events if (
                event.type == EVENTS.BRANCH_PROGRESS and event.branch_id == branch_id
            )]
            # The durable event must already exist when this proposal begins.
            assert progress[-1].payload == {
                "attempt": model_calls[branch_id], "max_attempts": 3,
            }
            model_started.set()
            if cancel_during_proposal:
                await asyncio.Event().wait()
            await asyncio.sleep(0)  # Exercise concurrent branch callback closures.
            path = (
                "../outside.py" if branch_id == "minimal" and model_calls[branch_id] == 1
                else "src/app/models.py"
            )
            return PatchProposal(
                replacements=[FileReplacement(
                    path=path, lines=["from pydantic import field_validator"],
                )], summary="Synthetic proposal",
            )

    class SyntheticSandbox:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def run(self, parent, command, *, timeout_seconds):
            parents.append(parent)
            checkpoint = f"synthetic-child-{len(parents)}"
            await asyncio.sleep(0)
            markers = {
                "TEST_EXIT": 0, "PIP_EXIT": 0, "RUFF_EXIT": 0,
                "TESTS_COLLECTED": 1, "TESTS_PASSED": 1, "TESTS_FAILED": 0,
                "PYDANTIC_MAJOR": 2, "INSTALL_EXIT": 0,
                "CONTRACT_BEFORE": contract, "CONTRACT_AFTER": contract,
            }
            if outcome == "revalidation_failed" and len(parents) == 4:
                markers.update(TEST_EXIT=1, TESTS_PASSED=0, TESTS_FAILED=1)
            return CommandResult(
                state=SandboxState(checkpoint_id=checkpoint),
                stdout="\n".join(f"__BRANCHSHIFT_{key}={value}" for key, value in markers.items())
                + "\nRetained synthetic check output",
                stderr="", exit_code=0, elapsed_seconds=0.01,
            )

    monkeypatch.setattr(run_manager, "NebiusModelProvider", lambda *args, **kwargs: ObservedModel())
    monkeypatch.setattr(
        run_manager, "ContreeSandboxProvider", lambda *args, **kwargs: SyntheticSandbox(),
    )
    created = await manager.create(CreateRunRequest(
        repo_url="https://github.com/owner/repo", baseline_ref="d" * 40,
    ))
    if cancel_during_proposal:
        await asyncio.wait_for(model_started.wait(), timeout=1)
        await manager.shutdown()
    else:
        await asyncio.wait_for(manager.wait(created.id), timeout=2)
        await manager.shutdown()
    repository.close()

    reopened = RunRepository(database_url)
    try:
        summary = await reopened.require_run(created.id)
        events = await reopened.list_events(created.id)
        expected_status = {
            "cancelled": RunStatus.CANCELLED, "completed": RunStatus.COMPLETED,
            "revalidation_failed": RunStatus.FAILED,
        }[outcome]
        assert summary.status is expected_status
        if outcome == "completed":
            assert any(
                event.message == "Patch checks passed in a Pydantic 2 environment"
                for event in events
            )
            assert not any("migration package ready" in event.message for event in events)
        for field, value in provenance.items():
            assert getattr(summary, field) == value
        assert summary.baseline_commit_sha == baseline.commit_sha
        assert summary.baseline_ref == baseline.commit_sha
        assert summary.baseline_checkpoint_id == baseline.state.checkpoint_id
        assert summary.runtime_config_digest == created.runtime_config_digest
        assert [event.id for event in events] == list(range(1, len(events) + 1))
        assert all(event.run_id == created.id for event in events)
        assert model_calls
        for branch_id, calls in model_calls.items():
            branch_events = [event for event in events if event.branch_id == branch_id]
            progress = [event for event in branch_events if event.type == EVENTS.BRANCH_PROGRESS]
            assert [event.payload for event in progress] == [
                {"attempt": attempt, "max_attempts": 3} for attempt in range(1, calls + 1)
            ]
            assert branch_events[0].type == EVENTS.BRANCH_STARTED
            assert all("started" in event.message for event in progress)
            if cancel_during_proposal:
                assert branch_events[-1] is progress[-1]
            else:
                completed = next(event for event in branch_events if (
                    event.type == EVENTS.BRANCH_COMPLETED
                ))
                assert completed.id > progress[-1].id
        if cancel_during_proposal:
            assert parents == []
            assert all(calls == 1 for calls in model_calls.values())
        else:
            assert model_calls == {"minimal": 2, "compatibility": 1, "refactor": 1}
            assert parents == [baseline.state] * 4  # Three branches plus clean revalidation.
            assert len(summary.branches) == 3
            assert summary.revalidation is not None
        if outcome == "revalidation_failed":
            assert summary.revalidation.tests_failed == 1
            assert summary.revalidation.tests_passed == 0
            assert summary.revalidation.test_exit_code == 1
            assert summary.revalidated_checkpoint_id == "synthetic-child-4"
            assert "Retained synthetic check output" in summary.revalidation.diagnostics
            assert all(branch.tests_passed == 1 for branch in summary.branches)
            assert summary.winner_id is None and summary.patch is None
            assert summary.failure_reason == "Winner patch failed clean baseline revalidation"
            assert not any(event.type == EVENTS.WINNER_SELECTED for event in events)
            assert events[-1].type == EVENTS.RUN_FAILED

            # Exercise the public exports after a database close/reopen, not only the object.
            app = create_app(Settings(mode="mock", database_url=database_url))
            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test",
                ) as client:
                    report = await client.get(f"/api/runs/{created.id}/report")
                    assert report.status_code == 200
                    stored = report.json()["run"]
                    assert stored["revalidation"]["tests_failed"] == 1
                    assert stored["revalidation"]["checkpoint_id"] == "synthetic-child-4"
                    assert stored["winner_id"] is None and stored["patch"] is None
                    markdown = await client.get(f"/api/runs/{created.id}/report?format=markdown")
                    assert markdown.status_code == 200
                    assert "Clean-baseline revalidation did not pass" in markdown.text
                    assert "Retained synthetic check output" in markdown.text
                    assert "Passing live patch checks are not established" in markdown.text
                    assert (await client.get(f"/api/runs/{created.id}/patch")).status_code == 409
            finally:
                app.state.repository.close()
    finally:
        reopened.close()
