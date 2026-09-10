import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.models import CreateRunRequest, RunStatus, RunSummary
from app.main import create_app
from app.orchestrator.run_manager import RunManager
from app.storage.repositories import RunRepository


@pytest.mark.parametrize("start_tasks", [True, False])
async def test_shutdown_retains_active_and_queued_runs(tmp_path, monkeypatch, start_tasks):
    database_url = f"sqlite:///{tmp_path / 'shutdown.db'}"
    repository = RunRepository(database_url)
    manager = RunManager(repository, Settings(database_url=database_url, max_concurrent_runs=1))
    started = asyncio.Event()

    async def execute(run_id):
        await repository.set_status(run_id, RunStatus.PREPARING, "Preparing baseline")
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(manager, "_execute", execute)
    request = CreateRunRequest(repo_url="https://github.com/owner/repo")
    first = await manager.create(request)
    second = await manager.create(request)
    if start_tasks:
        await asyncio.wait_for(started.wait(), timeout=1)
    await manager.shutdown()
    repository.close()

    reopened = RunRepository(database_url)
    for run_id in (first.id, second.id):
        summary = await reopened.require_run(run_id)
        assert summary.status is RunStatus.CANCELLED
        assert summary.failure_reason == "Server stopped before this run finished"
        events = await reopened.list_events(run_id)
        assert events[-1].payload["status"] == "cancelled"
        assert sum(event.payload.get("status") == "cancelled" for event in events) == 1
    reopened.close()


def test_startup_recovers_interrupted_runs_without_changing_finished_evidence(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'restart.db'}"

    async def seed():
        repository = RunRepository(database_url)
        await repository.create_run(RunSummary(
            id="interrupted", repo_url="https://github.com/owner/repo",
            status=RunStatus.BRANCHING, baseline_commit_sha="abc123",
        ))
        await repository.create_run(RunSummary(
            id="finished", repo_url="https://github.com/owner/repo",
            status=RunStatus.FAILED, failure_reason="Original diagnostic",
        ))
        repository.close()

    asyncio.run(seed())
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        recovered = client.get("/api/runs/interrupted").json()
        finished = client.get("/api/runs/finished").json()
        report = client.get("/api/runs/interrupted/report").json()
    assert recovered["status"] == "cancelled"
    assert recovered["baseline_commit_sha"] == "abc123"
    assert finished["status"] == "failed"
    assert finished["failure_reason"] == "Original diagnostic"
    assert report["events"][-1]["payload"]["status"] == "cancelled"
