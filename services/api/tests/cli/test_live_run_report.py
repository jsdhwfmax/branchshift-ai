import json
from pathlib import Path

import pytest

from app.cli import live_run
from app.config import Settings
from app.domain.models import RunStatus, RunSummary
from app.reports import render_markdown_report
from app.storage.repositories import RunRepository


@pytest.mark.parametrize("completed", [True, False])
async def test_cli_exports_matching_markdown_without_provider_calls(
    tmp_path, monkeypatch, completed
):
    source = Path(__file__).resolve().parents[4] / "evaluation/evidence/6d863a18d814.json"
    run = RunSummary.model_validate_json(source.read_text())
    if not completed:
        run.status = RunStatus.FAILED
        run.failure_reason = "do-not-disclose-key"
        run.winner_id = None
        run.patch = None
        run.revalidation = None

    class RetainedResultManager:
        def __init__(self, repository, config):
            self.repository = repository

        async def create(self, request):
            return await self.repository.create_run(run)

        async def wait(self, run_id):
            pass

        async def shutdown(self):
            pass

    monkeypatch.setattr(live_run, "RunManager", RetainedResultManager)
    monkeypatch.setattr(
        live_run,
        "settings",
        Settings(mode="mock", nebius_api_key="do-not-disclose-key", tavily_api_key=""),
    )
    assert await live_run.execute(str(run.repo_url), tmp_path) is completed
    raw = json.loads((tmp_path / f"{run.id}.json").read_text())
    markdown = (tmp_path / f"{run.id}.md").read_text()
    assert "do-not-disclose-key" not in markdown
    repository = RunRepository(f"sqlite:///{tmp_path / 'runs.db'}")
    events = await repository.list_events(run.id)
    repository.close()
    assert markdown == render_markdown_report(RunSummary.model_validate(raw), events)
    if completed:
        assert (tmp_path / f"{run.id}.patch").read_text() == run.patch
    else:
        assert not (tmp_path / f"{run.id}.patch").exists()
        assert "Successful live migration is not established" in markdown
