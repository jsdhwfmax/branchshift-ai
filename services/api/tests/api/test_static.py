from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_built_app_routes_cache_headers_and_api_boundary(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "index.html").write_text("<h1>BranchShift</h1>")
    (assets / "app-hash.js").write_text("console.log('app')")
    config = Settings(mode="mock", database_url="sqlite:///:memory:")
    with TestClient(create_app(config, web_dist=tmp_path)) as client:
        assert "BranchShift" in client.get("/").text
        nested = client.get("/runs/123")
        assert nested.status_code == 200
        assert nested.headers["cache-control"] == "no-cache"
        assert "immutable" in client.get("/assets/app-hash.js").headers["cache-control"]
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/missing").status_code == 404
        assert client.get("/api/health/integrations").json()["mode"] == "mock"
        assert client.get("/%2e%2e/secret.txt").status_code == 404
