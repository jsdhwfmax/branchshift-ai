import base64
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from app.api import judge_auth
from app.config import Settings
from app.main import create_app

USERNAME = "judges"
PASSWORD = "M7q_G2v-9jPw4zL6xRt3cK8nYs5bHd0F"
PAYLOAD = {"repo_url": "https://github.com/owner/repo"}
AUTH_VARS = (
    "BRANCHSHIFT_AUTH_USERNAME",
    "BRANCHSHIFT_AUTH_PASSWORD",
    "BRANCHSHIFT_REQUIRE_AUTH",
)


@pytest.fixture(autouse=True)
def isolated_auth_environment(monkeypatch):
    for name in AUTH_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")


def authorization(username=USERNAME, password=PASSWORD):
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": "Basic " + encoded}


def private_config(tmp_path, **overrides):
    return Settings(
        mode="mock",
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        mock_step_delay_seconds=0.001,
        auth_username=SecretStr(USERNAME),
        auth_password=SecretStr(PASSWORD),
        **overrides,
    )


def counts(tmp_path):
    with sqlite3.connect(tmp_path / "auth.db") as connection:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("runs", "http_admissions")
        )


def test_unconfigured_settings_disable_auth_without_exposing_credentials():
    settings = Settings()
    assert settings.auth_username is settings.auth_password is None
    assert settings.require_auth is False
    protected = Settings(auth_username=SecretStr(USERNAME), auth_password=SecretStr(PASSWORD))
    assert USERNAME not in repr(protected) and PASSWORD not in repr(protected)
    assert isinstance(protected.auth_password, SecretStr)


@pytest.mark.parametrize(
    "username,password",
    [
        (None, PASSWORD),
        (USERNAME, None),
        ("", PASSWORD),
        (USERNAME, ""),
        ("space user", PASSWORD),
        ("user:name", PASSWORD),
        ("bad\nuser", PASSWORD),
        (USERNAME, "password"),
        (USERNAME, "a" * 64),
        (USERNAME, PASSWORD + " "),
        (USERNAME, PASSWORD + "\x00"),
        (USERNAME, "x" * 513),
    ],
)
def test_partial_empty_and_weak_credentials_fail_without_echo(username, password):
    with pytest.raises(ValueError) as caught:
        Settings(
            auth_username=None if username is None else SecretStr(username),
            auth_password=None if password is None else SecretStr(password),
        )
    for value in (username, password):
        if value and len(value) > 15:
            assert value not in str(caught.value)


def test_required_auth_cannot_start_without_both_credentials(monkeypatch):
    monkeypatch.setenv("BRANCHSHIFT_REQUIRE_AUTH", "true")
    with pytest.raises(ValueError, match="credentials are missing"):
        Settings()
    monkeypatch.setenv("BRANCHSHIFT_AUTH_USERNAME", USERNAME)
    monkeypatch.setenv("BRANCHSHIFT_AUTH_PASSWORD", PASSWORD)
    configured = Settings()
    assert configured.require_auth is True
    assert configured.auth_username.get_secret_value() == USERNAME
    monkeypatch.setenv("BRANCHSHIFT_AUTH_PASSWORD", "")
    with pytest.raises(ValueError, match="password must contain"):
        Settings()
    monkeypatch.setenv("BRANCHSHIFT_REQUIRE_AUTH", "tru")
    with pytest.raises(ValueError, match="must be true or false"):
        Settings()


def test_raw_strings_cannot_accidentally_bypass_secret_storage():
    with pytest.raises(ValueError, match="SecretStr"):
        Settings(auth_username=USERNAME, auth_password=PASSWORD)


def test_module_startup_rejects_missing_required_credentials_without_loading_dotenv(tmp_path):
    # A hostile local .env would enable live mode if this test accidentally read it.
    (tmp_path / ".env").write_text(
        "BRANCHSHIFT_MODE=live\nBRANCHSHIFT_AUTH_PASSWORD=dotenv-secret\n"
    )
    environment = os.environ.copy()
    for name in AUTH_VARS:
        environment.pop(name, None)
    environment.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "BRANCHSHIFT_MODE": "mock",
            "DATABASE_URL": "sqlite:///:memory:",
            "BRANCHSHIFT_REQUIRE_AUTH": "true",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "credentials are missing" in result.stderr
    assert "dotenv-secret" not in result.stderr + result.stdout


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/"),
        ("GET", "/assets/app.js"),
        ("GET", "/runs/stored"),
        ("GET", "/api/health/integrations"),
        ("GET", "/api/runs"),
        ("GET", "/api/runs/missing"),
        ("GET", "/api/runs/missing/report"),
        ("GET", "/api/runs/missing/patch"),
        ("GET", "/api/runs/missing/events"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("GET", "/api/"),
        ("GET", "/%61pi"),
        ("HEAD", "/api"),
        ("POST", "/api"),
        ("OPTIONS", "/api/runs"),
        ("POST", "/api/runs"),
    ],
)
async def test_entire_site_protected_except_exact_get_health(tmp_path, method, path):
    app = create_app(private_config(tmp_path))
    app.state.manager.create = AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://judge.example",
    ) as client:
        response = await client.request(method, path)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == (
            'Basic realm="BranchShift judging", charset="UTF-8"'
        )
        assert response.headers["cache-control"] == "no-store"
        health = await client.get("/api")
        assert health.status_code == 200 and health.json()["status"] == "ready"
    app.state.manager.create.assert_not_awaited()
    app.state.repository.close()
    assert counts(tmp_path) == (0, 0)


@pytest.mark.parametrize(
    "header",
    [
        b"",
        b"Bearer not-a-password",
        b"Basic !!!",
        b"Basic",
        b"Basic YWJj",
        b"Basic /w==",
        b"Basic " + b"A" * 4096,
        b"Basic " + base64.b64encode("wrong:\u540d\u5bc6\u7801".encode()),
        b"Basic " + base64.b64encode(f"{USERNAME}:wrong-password".encode()),
    ],
)
async def test_invalid_authorization_is_generic_and_precedes_csrf(tmp_path, header):
    app = create_app(private_config(tmp_path))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://judge.example",
    ) as client:
        response = await client.post(
            "/api/runs",
            json=PAYLOAD,
            headers=[
                (b"authorization", header),
                (b"origin", b"https://attacker.example"),
            ],
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required."}
        assert PASSWORD not in response.text
    app.state.repository.close()
    assert counts(tmp_path) == (0, 0)


async def test_utf8_credentials_and_both_fixed_length_comparisons(tmp_path, monkeypatch):
    username = "\u8bc4\u59d4"
    config = private_config(tmp_path)
    from dataclasses import replace

    app = create_app(replace(config, auth_username=SecretStr(username)))
    comparisons = []
    original = judge_auth.secrets.compare_digest

    def compare(left, right):
        comparisons.append((len(left), len(right)))
        return original(left, right)

    monkeypatch.setattr(judge_auth.secrets, "compare_digest", compare)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://judge.example",
    ) as client:
        assert (
            await client.get("/api/health/integrations", headers=authorization(username))
        ).status_code == 200
        assert (
            await client.get("/api/health/integrations", headers=authorization("wrong"))
        ).status_code == 401
    app.state.repository.close()
    assert comparisons == [(32, 32)] * 4


async def test_authorized_static_resources_private_and_default_behavior_unchanged(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Judge app</h1>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app.js").write_text("console.log('app')")
    for config, headers, expected_cache in (
        (private_config(tmp_path), authorization(), "private, no-store"),
        (Settings(mode="mock", database_url="sqlite:///:memory:"), {}, "public"),
    ):
        app = create_app(config, web_dist=tmp_path)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://judge.example",
        ) as client:
            for path in ("/", "/runs/stored", "/assets/app.js", "/api/health/integrations"):
                response = await client.get(path, headers=headers)
                assert response.status_code == 200
            asset = await client.get("/assets/app.js", headers=headers)
            assert expected_cache in asset.headers["cache-control"]
        app.state.repository.close()


@pytest.mark.parametrize(
    "origin,site,status",
    [
        (None, None, 202),
        ("https://judge.example", "same-origin", 202),
        ("https://judge.example:443", None, 202),
        (None, "same-origin", 202),
        ("https://attacker.example", "same-origin", 403),
        ("https://judge.example", "cross-site", 403),
        ("https://judge.example", "same-site", 403),
        (None, "cross-site", 403),
        ("null", None, 403),
        ("http://judge.example", "same-origin", 403),
        ("https://judge.example:444", None, 403),
        ("https://judge.example/", None, 403),
        ("https://u@judge.example", None, 403),
        (None, "forged", 403),
    ],
)
async def test_private_writes_csrf_and_tls_terminating_proxy(tmp_path, origin, site, status):
    app = create_app(private_config(tmp_path))
    headers = authorization()
    if origin is not None:
        headers["Origin"] = origin
    if site is not None:
        headers["Sec-Fetch-Site"] = site
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            # Simulate HTTPS ingress forwarding HTTP, without trusted proxy headers.
            transport=httpx.ASGITransport(app=app),
            base_url="http://judge.example",
        ) as client,
    ):
        response = await client.post("/api/runs", json=PAYLOAD, headers=headers)
        assert response.status_code == status
        if status == 202:
            await app.state.manager.wait(response.json()["id"])
    assert counts(tmp_path) == ((1, 1) if status == 202 else (0, 0))


async def test_loopback_origin_supported_and_forwarding_cannot_override_host(tmp_path):
    app = create_app(private_config(tmp_path, http_lifetime_run_limit=0))
    headers = authorization() | {"Origin": "http://127.0.0.1:8000", "Sec-Fetch-Site": "same-origin"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8000",
    ) as client:
        assert (await client.post("/api/runs", json=PAYLOAD, headers=headers)).status_code == 429
        forged = authorization() | {
            "Origin": "https://attacker.example",
            "X-Forwarded-Host": "attacker.example",
            "X-Forwarded-Proto": "https",
            "Forwarded": "host=attacker.example;proto=https",
        }
        assert (await client.post("/api/runs", json=PAYLOAD, headers=forged)).status_code == 403
        duplicate = [(key.encode(), value.encode()) for key, value in authorization().items()]
        duplicate += [
            (b"origin", b"https://attacker.example"),
            (b"origin", b"https://127.0.0.1:8000"),
        ]
        assert (await client.post("/api/runs", json=PAYLOAD, headers=duplicate)).status_code == 403
        duplicate_auth = list(authorization().items()) * 2
        assert (
            await client.post("/api/runs", json=PAYLOAD, headers=duplicate_auth)
        ).status_code == 401
    app.state.repository.close()
    assert counts(tmp_path) == (0, 0)


async def test_unauthenticated_request_does_not_read_body_or_call_manager(tmp_path):
    app = create_app(private_config(tmp_path))
    app.state.manager.create = AsyncMock()
    sent = []

    async def receive():
        raise AssertionError("Unauthenticated body must not be consumed")

    async def send(message):
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/runs",
            "raw_path": b"/api/runs",
            "query_string": b"",
            "root_path": "",
            "client": ("198.51.100.1", 1234),
            "server": ("judge.example", 443),
            "headers": [(b"content-length", b"999999")],
        },
        receive,
        send,
    )
    assert sent[0]["status"] == 401
    app.state.manager.create.assert_not_awaited()
    app.state.repository.close()
    assert counts(tmp_path) == (0, 0)


async def test_authenticated_request_still_obeys_body_limit_before_admission(tmp_path):
    app = create_app(private_config(tmp_path, http_max_body_bytes=32))
    app.state.manager.create = AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://judge.example",
    ) as client:
        response = await client.post("/api/runs", json=PAYLOAD, headers=authorization())
        assert response.status_code == 413
    app.state.manager.create.assert_not_awaited()
    app.state.repository.close()
    assert counts(tmp_path) == (0, 0)


async def test_authenticated_admission_stays_persistent_and_evidence_remains_readable(tmp_path):
    config = private_config(tmp_path, http_lifetime_run_limit=1)
    run_id = None
    for first_start in (True, False):
        app = create_app(config)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://judge.example",
            ) as client,
        ):
            response = await client.post("/api/runs", json=PAYLOAD, headers=authorization())
            assert response.status_code == (202 if first_start else 429)
            if first_start:
                run_id = response.json()["id"]
                await app.state.manager.wait(run_id)
            else:
                assert "allowance is exhausted" in response.json()["detail"]
                for suffix in ("", "/patch", "/report", "/report?format=markdown", "/events"):
                    path = f"/api/runs/{run_id}{suffix}"
                    assert (await client.get(path)).status_code == 401
                    assert (await client.get(path, headers=authorization())).status_code == 200
                app.state.manager.create = AsyncMock()
                denied = await client.post("/api/runs", json=PAYLOAD)
                assert denied.status_code == 401
                app.state.manager.create.assert_not_awaited()
        assert counts(tmp_path) == (1, 1)
