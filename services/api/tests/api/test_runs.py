import time

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_mock_run_completes_and_exports_patch(tmp_path):
    config = Settings(
        mode="mock",
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        mock_step_delay_seconds=0.001,
    )
    with TestClient(create_app(config)) as client:
        created = client.post(
            "/api/runs", json={"repo_url": "https://github.com/owner/repo"}
        )
        assert created.status_code == 202
        run_id = created.json()["id"]

        deadline = time.monotonic() + 2
        summary = created.json()
        while summary["status"] not in {"completed", "failed"} and time.monotonic() < deadline:
            summary = client.get(f"/api/runs/{run_id}").json()
            time.sleep(0.01)

        assert summary["status"] == "completed"
        assert summary["winner_id"] == "minimal"
        assert len(summary["branches"]) == 3
        patch = client.get(f"/api/runs/{run_id}/patch")
        assert patch.status_code == 200
        assert "field_validator" in patch.text
        report = client.get(f"/api/runs/{run_id}/report")
        assert report.status_code == 200
        assert report.json()["evidence_scope"] == "illustrative sample"
        assert report.json()["run"]["winner_id"] == "minimal"
        assert report.json()["events"][-1]["type"] == "run.completed"


def test_health_never_exposes_secret(tmp_path):
    config = Settings(
        mode="mock",
        database_url=f"sqlite:///{tmp_path / 'health.db'}",
        nebius_api_key="do-not-return-me",
        tavily_api_key="also-secret",
    )
    with TestClient(create_app(config)) as client:
        response = client.get("/api/health/integrations")
    assert response.status_code == 200
    assert "do-not-return-me" not in response.text
    assert response.json()["integrations"]["nemotron"]["configured"] is True


def test_live_health_requires_sandbox_project(tmp_path):
    config = Settings(
        mode="live", database_url=f"sqlite:///{tmp_path / 'project-health.db'}",
        nebius_api_key="test", nebius_project_id="", tavily_api_key="test",
    )
    with TestClient(create_app(config)) as client:
        health = client.get("/api/health/integrations").json()
    assert health["ready"] is False
    assert health["integrations"]["contree"]["configured"] is False


def test_live_run_without_credentials_fails_safely(tmp_path):
    config = Settings(
        mode="live",
        database_url=f"sqlite:///{tmp_path / 'live-missing.db'}",
        nebius_api_key="",
        nebius_project_id="",
        tavily_api_key="",
    )
    with TestClient(create_app(config)) as client:
        created = client.post(
            "/api/runs",
            json={"repo_url": "https://github.com/jsdhwfmax/branchshift-ai"},
        )
        run_id = created.json()["id"]
        deadline = time.monotonic() + 2
        summary = created.json()
        while summary["status"] == "queued" and time.monotonic() < deadline:
            summary = client.get(f"/api/runs/{run_id}").json()
            time.sleep(0.01)

    assert summary["status"] == "failed"
    assert summary["failure_reason"] == (
        "Live mode requires configured Nebius key, project, and Tavily credentials"
    )
