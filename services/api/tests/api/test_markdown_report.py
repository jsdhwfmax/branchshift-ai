import httpx

from app.config import Settings
from app.domain.models import RunStatus, RunSummary
from app.main import create_app
from app.reports import render_markdown_report


async def test_report_json_compatibility_and_markdown_download_with_closed_admission(tmp_path):
    app = create_app(
        Settings(
            mode="mock", database_url=f"sqlite:///{tmp_path / 'api.db'}", http_lifetime_run_limit=0
        )
    )
    run = RunSummary(
        id="partial",
        repo_url="https://github.com/owner/repo",
        mode="live",
        status=RunStatus.FAILED,
        failure_reason="Retained partial evidence",
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        await app.state.repository.create_run(run)
        events = await app.state.repository.list_events(run.id)
        default = await client.get("/api/runs/partial/report")
        explicit_json = await client.get("/api/runs/partial/report?format=json")
        assert default.status_code == 200 and default.text == explicit_json.text
        assert default.json() == {
            "schema_version": 1,
            "evidence_scope": "live providers",
            "run": run.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in events],
        }
        markdown = await client.get("/api/runs/partial/report?format=markdown")
        stored = await app.state.repository.require_run(run.id)
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert 'filename="partial-evidence.md"' in markdown.headers["content-disposition"]
        assert markdown.text == render_markdown_report(stored, events)
        assert "Successful live migration is not established" in markdown.text
        assert (await client.get("/api/runs/partial/report?format=html")).status_code == 422
        assert (await client.get("/api/runs/missing/report?format=markdown")).status_code == 404
