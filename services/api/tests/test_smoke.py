from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_api_smoke(tmp_path):
    config = Settings(database_url=f"sqlite:///{tmp_path / 'smoke.db'}")
    with TestClient(create_app(config)) as client:
        response = client.get("/api")
    assert response.status_code == 200
    assert response.json() == {"name": "BranchShift", "status": "ready"}

