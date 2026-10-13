from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.domain.models import CreateRunRequest
from app.orchestrator import run_manager
from app.orchestrator.baseline import repository_workdir
from app.orchestrator.run_manager import RunManager
from app.storage.repositories import RunRepository


@pytest.mark.parametrize("mode", ["live", "mock"])
@pytest.mark.parametrize("url, requested, live_expected", [
    ("https://github.com/jsdhwfmax/branchshift-ai", None, "fixtures/pydantic-v1-app"),
    ("https://github.com/jsdhwfmax/branchshift-ai.git", None, "fixtures/pydantic-v1-app"),
    ("https://github.com/jsdhwfmax/branchshift-ai/", None, "fixtures/pydantic-v1-app"),
    ("https://github.com/jsdhwfmax/branchshift-ai", "packages/models", "packages/models"),
    ("https://github.com/owner/repo", None, None),
    ("https://github.com/owner/repo", "packages/models", "packages/models"),
])
async def test_new_runs_record_effective_project_path_without_rewriting_samples(
    tmp_path, monkeypatch, mode, url, requested, live_expected,
):
    monkeypatch.setattr(run_manager, "source_provenance", lambda: {})
    database_url = f"sqlite:///{tmp_path / 'paths.db'}"
    repository = RunRepository(database_url)
    manager = RunManager(repository, Settings(mode=mode, database_url=database_url))
    execute = AsyncMock()
    monkeypatch.setattr(manager, "_execute_guarded", execute)
    created = await manager.create(CreateRunRequest(repo_url=url, project_path=requested))
    await manager.wait(created.id)
    expected = live_expected if mode == "live" else requested
    assert created.project_path == expected
    execute.assert_awaited_once_with(created.id)
    repository.close()

    reopened = RunRepository(database_url)
    try:
        retained = await reopened.require_run(created.id)
        assert retained.project_path == expected
        if mode == "live":
            assert repository_workdir(retained.repo_url, retained.project_path) == (
                f"/workspace/repo/{expected}" if expected else "/workspace/repo"
            )
    finally:
        reopened.close()
