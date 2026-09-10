import json
from dataclasses import replace
from pathlib import Path

from app.config import Settings
from app.main import create_app

SNAPSHOT = Path(__file__).resolve().parents[4] / "docs/evidence/openapi.json"


def safe_schema_settings(tmp_path):
    # Explicit mock settings isolate schema generation from developer credentials,
    # runtime URLs and databases. No lifespan or provider execution is needed.
    return Settings(
        mode="mock", database_url=f"sqlite:///{tmp_path / 'openapi-private.db'}",
        mock_step_delay_seconds=0, run_timeout_seconds=30, max_concurrent_runs=1,
        http_max_body_bytes=8192, http_daily_run_limit=5, http_lifetime_run_limit=20,
        http_max_pending_runs=2, http_client_daily_run_limit=2,
        http_client_max_outstanding_runs=1,
        nebius_api_key="schema-private-nebius-key", nebius_project_id="schema-private-project",
        nebius_base_url="https://schema-private.invalid/inference/",
        nemotron_model="schema-private-model", nemotron_enable_thinking=False,
        tavily_api_key="schema-private-tavily-key",
        contree_api_url="https://schema-private.invalid/sandboxes",
        contree_image="schema-private-image",
    )


def schema_for(config, tmp_path):
    app = create_app(config, web_dist=tmp_path / "no-web-build")
    try:
        return app.openapi()
    finally:
        app.state.repository.close()


def test_public_openapi_contract_matches_reviewed_snapshot(tmp_path):
    actual = schema_for(safe_schema_settings(tmp_path), tmp_path)
    expected = json.loads(SNAPSHOT.read_text())
    assert actual == expected, (
        "The public OpenAPI contract changed. Review the request/response diff and update "
        "docs/evidence/openapi.json deliberately; do not silently regenerate it in tests."
    )


def test_create_contract_documents_success_validation_and_admission_errors(tmp_path):
    schema = schema_for(safe_schema_settings(tmp_path), tmp_path)
    operation = schema["paths"]["/api/runs"]["post"]
    assert operation["requestBody"]["required"] is True
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CreateRunRequest",
    }
    assert set(operation["responses"]) == {"202", "413", "422", "429", "503"}
    assert operation["responses"]["202"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RunSummary",
    }
    for status in ("413", "429", "503"):
        response = operation["responses"][status]
        assert response["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/RunAdmissionError",
        }
    error_schema = schema["components"]["schemas"]["RunAdmissionError"]
    assert error_schema["required"] == ["detail"]
    assert error_schema["properties"]["detail"]["type"] == "string"
    assert "Retry-After" in operation["responses"]["429"]["headers"]
    assert "Retry-After" in operation["responses"]["503"]["headers"]


def test_runtime_secrets_and_limits_do_not_become_public_schema_defaults(tmp_path):
    config = safe_schema_settings(tmp_path)
    original = schema_for(config, tmp_path)
    altered = schema_for(replace(
        config, nebius_api_key="schema-private-replacement-key",
        tavily_api_key="schema-private-replacement-tavily", nemotron_model="schema-private-other",
        http_daily_run_limit=999, http_max_body_bytes=32768,
    ), tmp_path)
    assert original == altered
    serialized = json.dumps(original)
    for private_value in (
        "schema-private", "openapi-private.db", str(tmp_path), "nebius_api_key",
        "tavily_api_key", "database_url", "http_daily_run_limit",
    ):
        assert private_value not in serialized
