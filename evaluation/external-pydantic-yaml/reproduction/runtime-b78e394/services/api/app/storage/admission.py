from __future__ import annotations

import hashlib
import hmac
import ipaddress
import math
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.domain.models import TERMINAL_RUN_STATUSES


@dataclass(frozen=True)
class HTTPAdmission:
    settings: Settings
    peer: str


_http_admission: ContextVar[HTTPAdmission | None] = ContextVar("http_admission", default=None)


class AdmissionDenied(Exception):
    def __init__(self, detail: str, *, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.retry_after = retry_after


@contextmanager
def http_admission(settings: Settings, peer: str) -> Iterator[None]:
    """Only HTTP creates consume public quotas; direct operator/CLI creates bypass them."""
    token = _http_admission.set(HTTPAdmission(settings, peer))
    try:
        yield
    finally:
        _http_admission.reset(token)


def initialize_admission(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS http_admissions (
            run_id TEXT PRIMARY KEY,
            client_key TEXT NOT NULL,
            utc_day TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS http_admissions_day ON http_admissions(utc_day);
        CREATE INDEX IF NOT EXISTS http_admissions_client_day
            ON http_admissions(client_key, utc_day);
        CREATE TABLE IF NOT EXISTS http_admission_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO http_admission_metadata(key, value) VALUES ('client_salt', ?)",
        (secrets.token_hex(32),),
    )
    connection.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _peer_key(connection: sqlite3.Connection, peer: str) -> str:
    # Never read Forwarded / X-Forwarded-For. Uvicorn's proxy trust is a deployment setting.
    try:
        address = ipaddress.ip_address(peer)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        canonical = str(address)
    except ValueError:
        canonical = peer  # Unix/test transports share their stable ASGI peer identifier.
    salt = connection.execute(
        "SELECT value FROM http_admission_metadata WHERE key = 'client_salt'"
    ).fetchone()[0]
    return hmac.new(bytes.fromhex(salt), canonical.encode(), hashlib.sha256).hexdigest()


def admit_http_run(connection: sqlite3.Connection, run_id: str) -> None:
    """Called inside the same BEGIN IMMEDIATE transaction that inserts the run.

    No reservation survives without its run; failure rolls back both. The SQLite
    writer lock serializes separate connections as well as concurrent requests.
    Quota history is never refunded for a failed/cancelled run or deleted evidence.
    """
    admission = _http_admission.get()
    if admission is None:
        return
    settings = admission.settings
    now = _now()
    day = now.date().isoformat()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    until_tomorrow = max(1, math.ceil((tomorrow - now).total_seconds()))
    client = _peer_key(connection, admission.peer)
    lifetime, daily, client_daily = connection.execute(
        """SELECT COUNT(*), COALESCE(SUM(utc_day = ?), 0),
                  COALESCE(SUM(utc_day = ? AND client_key = ?), 0)
           FROM http_admissions""", (day, day, client),
    ).fetchone()
    if lifetime >= settings.http_lifetime_run_limit:
        raise AdmissionDenied(
            "The public run allowance is exhausted. Additional capacity requires the operator; "
            "existing run evidence remains available."
        )
    if daily >= settings.http_daily_run_limit:
        raise AdmissionDenied(
            "The daily public run limit is reached. Try again after 00:00 UTC; "
            "existing run evidence remains available.", retry_after=until_tomorrow,
        )
    if client_daily >= settings.http_client_daily_run_limit:
        raise AdmissionDenied(
            "This client has reached its daily run limit. Try again after 00:00 UTC; "
            "existing run evidence remains available.", retry_after=until_tomorrow,
        )
    terminal = sorted(status.value for status in TERMINAL_RUN_STATUSES)
    placeholders = ",".join("?" for _ in terminal)
    outstanding, client_outstanding = connection.execute(
        f"""SELECT COUNT(*), COALESCE(SUM(a.client_key = ?), 0)
            FROM runs r LEFT JOIN http_admissions a ON a.run_id = r.id
            WHERE json_extract(r.document, '$.status') NOT IN ({placeholders})""",
        (client, *terminal),
    ).fetchone()
    # Executing slots are reserved immediately, even before the asyncio task starts.
    capacity = settings.max_concurrent_runs + settings.http_max_pending_runs
    if outstanding >= capacity:
        raise AdmissionDenied(
            "All active and pending run slots are occupied. Wait for a run to finish; "
            "existing run evidence remains available.", retry_after=30,
        )
    if client_outstanding >= settings.http_client_max_outstanding_runs:
        raise AdmissionDenied(
            "This client already has the maximum number of unfinished runs. "
            "Wait for a run to finish before starting another.", retry_after=30,
        )
    connection.execute(
        "INSERT INTO http_admissions(run_id, client_key, utc_day) VALUES (?, ?, ?)",
        (run_id, client, day),
    )
