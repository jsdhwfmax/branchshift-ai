from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from app.domain.models import RunEvent, RunStatus, RunSummary, assert_transition, utc_now


def _database_path(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("BranchShift currently supports sqlite:/// database URLs only")
    path = database_url.removeprefix(prefix)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


class RunRepository:
    def __init__(self, database_url: str) -> None:
        self._connection = sqlite3.connect(_database_path(database_url), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()
        self._conditions: dict[str, asyncio.Condition] = {}
        self._connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                document TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                run_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                document TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence),
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );
            """
        )

    async def create_run(self, summary: RunSummary) -> RunSummary:
        async with self._lock:
            self._connection.execute(
                "INSERT INTO runs(id, document) VALUES (?, ?)",
                (summary.id, summary.model_dump_json()),
            )
            self._connection.commit()
        await self.append_event(
            summary.id,
            "run.status",
            "Run queued",
            payload={"status": "queued"},
        )
        return summary

    async def get_run(self, run_id: str) -> RunSummary | None:
        async with self._lock:
            row = self._connection.execute(
                "SELECT document FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        return RunSummary.model_validate_json(row["document"]) if row else None

    async def save_run(self, summary: RunSummary) -> RunSummary:
        summary.updated_at = utc_now()
        async with self._lock:
            self._connection.execute(
                "UPDATE runs SET document = ? WHERE id = ?",
                (summary.model_dump_json(), summary.id),
            )
            self._connection.commit()
        return summary

    async def set_status(self, run_id: str, next_status: RunStatus, message: str) -> RunSummary:
        summary = await self.require_run(run_id)
        assert_transition(summary.status, next_status)
        summary.status = next_status
        await self.save_run(summary)
        await self.append_event(
            run_id,
            "run.status",
            message,
            payload={"status": next_status.value},
        )
        return summary

    async def append_event(
        self,
        run_id: str,
        event_type: str,
        message: str,
        *,
        branch_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> RunEvent:
        async with self._lock:
            row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            event = RunEvent(
                id=int(row["next"]),
                run_id=run_id,
                type=event_type,
                message=message,
                branch_id=branch_id,
                payload=payload or {},
            )
            self._connection.execute(
                "INSERT INTO events(run_id, sequence, document) VALUES (?, ?, ?)",
                (run_id, event.id, event.model_dump_json()),
            )
            self._connection.commit()
        condition = self._conditions.setdefault(run_id, asyncio.Condition())
        async with condition:
            condition.notify_all()
        return event

    async def list_events(self, run_id: str, after: int = 0) -> list[RunEvent]:
        async with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM events WHERE run_id = ? AND sequence > ? ORDER BY sequence",
                (run_id, after),
            ).fetchall()
        return [RunEvent.model_validate_json(row["document"]) for row in rows]

    async def wait_for_events(
        self, run_id: str, after: int, timeout: float = 10.0
    ) -> list[RunEvent]:
        current = await self.list_events(run_id, after)
        if current:
            return current
        condition = self._conditions.setdefault(run_id, asyncio.Condition())
        try:
            async with condition:
                await asyncio.wait_for(condition.wait(), timeout=timeout)
        except TimeoutError:
            return []
        return await self.list_events(run_id, after)

    async def require_run(self, run_id: str) -> RunSummary:
        summary = await self.get_run(run_id)
        if summary is None:
            raise KeyError(run_id)
        return summary

    def close(self) -> None:
        self._connection.close()
