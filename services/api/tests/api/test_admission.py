import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings, _limit_env
from app.domain.models import RunStatus, RunSummary
from app.main import create_app
from app.storage import admission

PAYLOAD = {"repo_url": "https://github.com/owner/repo"}


def config_for(tmp_path, **overrides):
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'admission.db'}", mode="mock",
        mock_step_delay_seconds=0.001, **overrides,
    )


def counts(tmp_path):
    with sqlite3.connect(tmp_path / "admission.db") as connection:
        return tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                     for table in ("runs", "http_admissions"))


@pytest.mark.parametrize("length_headers", [
    [], [(b"content-length", b"1")], [(b"content-length", b"99999")],
    [(b"transfer-encoding", b"chunked")],
])
async def test_actual_stream_limit_precedes_parser_manager_and_storage(tmp_path, length_headers):
    app = create_app(config_for(tmp_path, http_max_body_bytes=100))
    app.state.manager.create = AsyncMock()
    messages = iter([
        {"type": "http.request", "body": b"x" * 70, "more_body": True},
        {"type": "http.request", "body": b"x" * 40, "more_body": True},
        {"type": "http.request", "body": b"never-read", "more_body": False},
    ])
    received = 0
    sent = []

    async def receive():
        nonlocal received
        received += 1
        return next(messages)

    async def send(message):
        sent.append(message)

    await app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/api/runs", "raw_path": b"/api/runs",
        "query_string": b"", "root_path": "", "client": ("198.51.100.1", 1234),
        "server": ("testserver", 80), "headers": [(b"content-type", b"application/json")]
        + length_headers,
    }, receive, send)
    app.state.manager.create.assert_not_awaited()
    app.state.repository.close()
    assert received == 2
    assert sent[0]["status"] == 413
    assert "100-byte limit" in json.loads(sent[1]["body"])["detail"]
    assert counts(tmp_path) == (0, 0)


async def test_exact_body_limit_and_invalid_payload_accounting(tmp_path):
    body = json.dumps(PAYLOAD).encode() + b" " * 20
    app = create_app(config_for(tmp_path, http_max_body_bytes=len(body)))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        invalid = await client.post("/api/runs", json={"repo_url": "http://localhost/repo"})
        assert invalid.status_code == 422
        assert counts(tmp_path) == (0, 0)
        accepted = await client.post(
            "/api/runs", content=body, headers={"Content-Type": "application/json"},
        )
        assert accepted.status_code == 202
        assert counts(tmp_path) == (1, 1)


async def test_concurrent_http_creates_cannot_overdraw_global_daily_limit(tmp_path, monkeypatch):
    app = create_app(config_for(
        tmp_path, http_daily_run_limit=1, http_client_daily_run_limit=50,
        http_client_max_outstanding_runs=50, http_max_pending_runs=50,
    ))
    execute = AsyncMock()

    async def wait_forever(run_id):
        await asyncio.Event().wait()

    execute.side_effect = wait_forever
    monkeypatch.setattr(app.state.manager, "_execute", execute)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        responses = await asyncio.gather(
            *(client.post("/api/runs", json=PAYLOAD) for _ in range(20))
        )
        await asyncio.sleep(0)
        assert [r.status_code for r in responses].count(202) == 1
        assert [r.status_code for r in responses].count(429) == 19
        assert counts(tmp_path) == (1, 1)
        assert execute.await_count == 1
        denied = next(r for r in responses if r.status_code == 429)
        assert "daily public run limit" in denied.json()["detail"]
        assert int(denied.headers["Retry-After"]) > 0


async def test_daily_rollover_lifetime_restart_and_read_access(tmp_path, monkeypatch):
    config = config_for(tmp_path, http_daily_run_limit=1, http_lifetime_run_limit=2)
    ids = []
    for day, expected in ((10, 202), (10, 429), (11, 202), (12, 429)):
        monkeypatch.setattr(
            admission, "_now", lambda day=day: datetime(2026, 9, day, tzinfo=timezone.utc),
        )
        app = create_app(config)
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            response = await client.post("/api/runs", json=PAYLOAD)
            if expected == 202:
                assert response.status_code == 202
                ids.append(response.json()["id"])
                await app.state.manager.wait(ids[-1])
                assert (await client.post("/api/runs", json=PAYLOAD)).status_code == 429
            elif day == 10:
                assert response.status_code == 429
                assert "daily public run limit" in response.json()["detail"]
                assert counts(tmp_path) == (1, 1)
            else:
                assert response.status_code == 429
                assert "allowance is exhausted" in response.json()["detail"]
                assert "Retry-After" not in response.headers
                for suffix in ("", "/patch", "/report", "/events"):
                    evidence = await client.get(f"/api/runs/{ids[0]}{suffix}")
                    assert evidence.status_code == 200
                assert counts(tmp_path) == (2, 2)


async def test_crash_recovery_frees_slots_without_refunding_admission(tmp_path):
    config = config_for(
        tmp_path, max_concurrent_runs=1, http_max_pending_runs=0,
        http_lifetime_run_limit=2, http_client_daily_run_limit=10,
    )
    # Simulate process loss after committed admission, before any worker starts.
    abandoned = create_app(config)
    with admission.http_admission(config, "127.0.0.1"):
        await abandoned.state.repository.create_run(RunSummary(id="interrupted", **PAYLOAD))
    abandoned.state.repository.close()
    restarted = create_app(config)
    async with restarted.router.lifespan_context(restarted), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=restarted), base_url="http://test",
    ) as client:
        recovered = await client.get("/api/runs/interrupted")
        assert recovered.json()["status"] == "cancelled"
        assert counts(tmp_path) == (1, 1)
        created = await client.post("/api/runs", json=PAYLOAD)
        assert created.status_code == 202  # No stale occupied slot after recovery.
        await restarted.state.manager.wait(created.json()["id"])
        rejected = await client.post("/api/runs", json=PAYLOAD)
        assert rejected.status_code == 429
        assert "allowance is exhausted" in rejected.json()["detail"]
        assert counts(tmp_path) == (2, 2)


async def test_active_pending_capacity_and_terminal_slot_release(tmp_path, monkeypatch):
    app = create_app(config_for(
        tmp_path, max_concurrent_runs=1, http_max_pending_runs=1,
        http_client_daily_run_limit=10, http_client_max_outstanding_runs=10,
    ))
    released = asyncio.Event()
    executing = []

    async def execute(run_id):
        executing.append(run_id)
        await app.state.repository.set_status(run_id, RunStatus.PREPARING, "Started")
        await released.wait()
        raise RuntimeError("Test terminal failure")

    monkeypatch.setattr(app.state.manager, "_execute", execute)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        first = await client.post("/api/runs", json=PAYLOAD)
        second = await client.post("/api/runs", json=PAYLOAD)
        rejected = await client.post("/api/runs", json=PAYLOAD)
        await asyncio.sleep(0)
        assert first.status_code == second.status_code == 202
        assert rejected.status_code == 429
        assert "active and pending run slots" in rejected.json()["detail"]
        assert len(executing) == 1  # Second task waits on the existing execution semaphore.
        assert counts(tmp_path) == (2, 2)
        released.set()
        await asyncio.gather(*(app.state.manager.wait(r.json()["id"]) for r in (first, second)))
        third = await client.post("/api/runs", json=PAYLOAD)
        assert third.status_code == 202
        assert counts(tmp_path) == (3, 3)  # Failed runs consumed allowance, but freed slots.


async def test_peer_quota_ignores_spoofed_forwarding_and_salt_survives_restart(tmp_path):
    config = config_for(tmp_path, http_client_daily_run_limit=1)
    first_key = None
    for iteration in range(2):
        app = create_app(config)
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("198.51.100.9", 1234)),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/runs", json=PAYLOAD, headers={
                "X-Forwarded-For": f"203.0.113.{iteration}", "Forwarded": "for=203.0.113.99",
            })
            if iteration == 0:
                assert response.status_code == 202
                await app.state.manager.wait(response.json()["id"])
                assert "198.51.100.9" not in response.text
                with sqlite3.connect(tmp_path / "admission.db") as connection:
                    first_key = connection.execute(
                        "SELECT client_key FROM http_admissions"
                    ).fetchone()[0]
                assert len(first_key) == 64
            else:
                assert response.status_code == 429
                assert "client has reached its daily" in response.json()["detail"]
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=("198.51.100.10", 1234)),
                base_url="http://test",
            ) as other_client:
                other = await other_client.post("/api/runs", json=PAYLOAD)
                assert other.status_code == (202 if iteration == 0 else 429)
        with sqlite3.connect(tmp_path / "admission.db") as connection:
            keys = [row[0] for row in connection.execute("SELECT client_key FROM http_admissions")]
        assert first_key in keys
        assert len(set(keys)) == 2


async def test_client_outstanding_limit_is_separate_from_global_slots(tmp_path, monkeypatch):
    app = create_app(config_for(tmp_path, http_client_daily_run_limit=5))

    async def wait_forever(run_id):
        await asyncio.Event().wait()

    monkeypatch.setattr(app.state.manager, "_execute", wait_forever)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        assert (await client.post("/api/runs", json=PAYLOAD)).status_code == 202
        rejected = await client.post("/api/runs", json=PAYLOAD)
        assert rejected.status_code == 429
        assert "maximum number of unfinished runs" in rejected.json()["detail"]
        assert counts(tmp_path) == (1, 1)


async def test_storage_lock_fails_closed_without_provider_work(tmp_path, monkeypatch):
    app = create_app(config_for(tmp_path))
    execute = AsyncMock()
    monkeypatch.setattr(app.state.manager, "_execute", execute)
    app.state.repository._connection.execute("PRAGMA busy_timeout=1")
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        with sqlite3.connect(tmp_path / "admission.db") as locked:
            locked.execute("BEGIN IMMEDIATE")
            response = await client.post("/api/runs", json=PAYLOAD)
            assert response.status_code == 503
        execute.assert_not_awaited()
        assert counts(tmp_path) == (0, 0)


async def test_zero_allowance_blocks_http_but_direct_operator_create_is_explicit(tmp_path):
    app = create_app(config_for(tmp_path, http_lifetime_run_limit=0))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        # Operator storage calls do not install the HTTP admission context.
        await app.state.repository.create_run(RunSummary(id="operator", **PAYLOAD))
        rejected = await client.post("/api/runs", json={**PAYLOAD, "mode": "mock", "bypass": True})
        assert rejected.status_code == 429
        assert counts(tmp_path) == (1, 0)
        assert (await client.get("/api/runs/operator/report")).status_code == 200


@pytest.mark.parametrize("overrides", [
    {"http_daily_run_limit": -1}, {"http_lifetime_run_limit": -1},
    {"http_max_body_bytes": 0}, {"http_max_pending_runs": -1}, {"max_concurrent_runs": 0},
])
def test_invalid_limits_do_not_start_an_unbounded_app(tmp_path, overrides):
    with pytest.raises(ValueError):
        config_for(tmp_path, **overrides)


def test_mistyped_environment_limit_fails_closed(monkeypatch):
    monkeypatch.setenv("HTTP_DAILY_RUN_LIMIT", "unlimited")
    with pytest.raises(ValueError):
        _limit_env("HTTP_DAILY_RUN_LIMIT", 5)
