import time

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_mock_run_completes_and_exports_patch(tmp_path):
    config = Settings(
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


def test_health_never_exposes_secret(tmp_path):
    config = Settings(
        database_url=f"sqlite:///{tmp_path / 'health.db'}",
        nebius_api_key="do-not-return-me",
        tavily_api_key="also-secret",
    )
    with TestClient(create_app(config)) as client:
        response = client.get("/api/health/integrations")
    assert response.status_code == 200
    assert "do-not-return-me" not in response.text
    assert response.json()["integrations"]["nemotron"]["configured"] is True

