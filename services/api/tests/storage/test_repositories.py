from app.domain.models import RunStatus, RunSummary
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

