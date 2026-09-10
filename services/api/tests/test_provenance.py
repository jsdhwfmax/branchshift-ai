from app.config import Settings
from app.provenance import runtime_config_digest, source_provenance


def test_source_fingerprint_changes_with_code_and_excludes_secrets(tmp_path):
    app = tmp_path / "services/api/app"
    app.mkdir(parents=True)
    source = app / "main.py"
    source.write_text("value = 1\n")
    (app.parent / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    secret = tmp_path / ".env"
    secret.write_text("NEBIUS_API_KEY=first-secret\n")
    first = source_provenance(app)
    secret.write_text("NEBIUS_API_KEY=second-secret\n")
    assert source_provenance(app)["orchestrator_digest"] == first["orchestrator_digest"]
    source.write_text("value = 2\n")
    assert source_provenance(app)["orchestrator_digest"] != first["orchestrator_digest"]
    assert first["orchestrator_revision"] is None
    assert "secret" not in str(first)


def test_repository_acceptance_limit_is_part_of_runtime_config_digest():
    first = runtime_config_digest(Settings(max_repository_bytes=1_000))
    assert runtime_config_digest(Settings(max_repository_bytes=1_001)) != first
    assert runtime_config_digest(Settings(
        max_repository_bytes=1_000, nebius_api_key="different-secret",
    )) == first
