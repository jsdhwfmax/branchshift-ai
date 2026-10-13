import asyncio
from datetime import datetime, timezone

from app.domain.models import BranchResult, BranchStatus, RunStatus, RunSummary
from app.storage.repositories import RunRepository


async def test_repository_persists_summary_and_ordered_events(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'runs.db'}"
    repository = RunRepository(database_url)
    summary = RunSummary(id="run-1", repo_url="https://github.com/owner/repo")
    await repository.create_run(summary)
    await repository.set_status("run-1", RunStatus.PREPARING, "Baseline ready")
    repository.close()

    reopened = RunRepository(database_url)
    stored = await reopened.require_run("run-1")
    events = await reopened.list_events("run-1")
    reopened.close()

    assert stored.status == RunStatus.PREPARING
    assert [event.id for event in events] == [1, 2]
    assert events[-1].message == "Baseline ready"


async def test_saved_run_index_is_bounded_durable_and_excludes_full_evidence(tmp_path):
    url = f"sqlite:///{tmp_path / 'recent.db'}"
    repository = RunRepository(url)
    for run_id, day in (("new-b", 3), ("old", 1), ("new-a", 3)):
        await repository.create_run(RunSummary(
            id=run_id, repo_url="https://github.com/owner/repo", mode="live",
            status=RunStatus.COMPLETED, created_at=datetime(2026, 10, day, tzinfo=timezone.utc),
            patch="large private source diff", report="diagnostic details",
            failure_reason="provider details",
        ))
    repository.close()
    reopened = RunRepository(url)
    results = await reopened.list_runs(2)
    reopened.close()
    assert [item.id for item in results] == ["new-b", "new-a"]
    assert set(results[0].model_dump()) == {
        "id", "repo_url", "project_path", "mode", "status", "created_at", "updated_at",
        "winner_id", "baseline_tests_collected",
    }


async def test_concurrent_branch_results_survive_reopen(tmp_path):
    url = f"sqlite:///{tmp_path / 'branches.db'}"
    repository = RunRepository(url)
    await repository.create_run(RunSummary(id="run", repo_url="https://github.com/owner/repo"))
    results = [
        BranchResult(
            strategy_id=name,
            status=BranchStatus.FAILED,
            tests_collected=1,
            tests_passed=0,
            tests_failed=1,
            pip_check_passed=True,
            lint_findings=0,
            changed_files=1,
            changed_lines=2,
            elapsed_seconds=1,
        )
        for name in ("minimal", "compatibility", "refactor")
    ]
    await asyncio.gather(*(repository.save_branch_result("run", item) for item in results))
    repository.close()
    reopened = RunRepository(url)
    stored = await reopened.require_run("run")
    reopened.close()
    assert {branch.strategy_id for branch in stored.branches} == {
        "minimal", "compatibility", "refactor",
    }
    assert len(stored.branches) == 3


async def test_event_wait_rechecks_durable_ledger_after_missed_notification(tmp_path):
    url = f"sqlite:///{tmp_path / 'event-race.db'}"
    reader = RunRepository(url)
    writer = RunRepository(url)
    await reader.create_run(RunSummary(id="run", repo_url="https://github.com/owner/repo"))
    pending = asyncio.create_task(reader.wait_for_events("run", 1, timeout=0.02))
    await asyncio.sleep(0)
    await writer.append_event("run", "run.failed", "Failure retained by another connection")
    events = await pending
    reader.close()
    writer.close()
    assert [event.type for event in events] == ["run.failed"]
