from __future__ import annotations

import json
import sqlite3
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from app.domain.models import TERMINAL_RUN_STATUSES, CreateRunRequest, RunSummary
from app.storage.admission import AdmissionDenied, http_admission

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunAdmissionError(BaseModel):
    detail: str


@router.post(
    "", response_model=RunSummary, status_code=status.HTTP_202_ACCEPTED,
    responses={
        413: {
            "model": RunAdmissionError,
            "description": "The actual request body exceeds the configured byte limit.",
        },
        429: {
            "model": RunAdmissionError,
            "description": (
                "A persistent public/client allowance or unfinished-run limit is reached."
            ),
            "headers": {"Retry-After": {
                "description": (
                    "Optional retry delay in seconds; absent for exhausted lifetime quota."
                ),
                "schema": {"type": "string", "pattern": "^[0-9]+$"},
            }},
        },
        503: {
            "model": RunAdmissionError,
            "description": "Admission storage is unavailable; no provider execution was started.",
            "headers": {"Retry-After": {
                "description": "Suggested retry delay in seconds.",
                "schema": {"type": "string", "pattern": "^[0-9]+$"},
            }},
        },
    },
)
async def create_run(payload: CreateRunRequest, request: Request) -> RunSummary:
    peer = request.client.host if request.client is not None else "unknown-peer"
    try:
        with http_admission(request.app.state.settings, peer):
            summary: RunSummary = await request.app.state.manager.create(payload)
    except AdmissionDenied as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
        raise HTTPException(status_code=429, detail=str(exc), headers=headers) from exc
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=503, detail="Run admission storage is unavailable. Try again shortly.",
            headers={"Retry-After": "1"},
        ) from exc
    return summary


@router.get("/{run_id}", response_model=RunSummary)
async def get_run(run_id: str, request: Request) -> RunSummary:
    summary: RunSummary | None = await request.app.state.repository.get_run(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return summary


@router.get("/{run_id}/patch", response_class=PlainTextResponse)
async def get_patch(run_id: str, request: Request) -> Response:
    summary = await request.app.state.repository.get_run(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not summary.patch:
        raise HTTPException(status_code=409, detail="Patch is not ready")
    return PlainTextResponse(
        summary.patch,
        headers={"Content-Disposition": f'attachment; filename="{run_id}-winner.patch"'},
    )


@router.get("/{run_id}/report")
async def get_report(run_id: str, request: Request) -> Response:
    summary = await request.app.state.repository.get_run(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = await request.app.state.repository.list_events(run_id)
    report = {
        "schema_version": 1,
        "evidence_scope": "live providers" if summary.mode == "live" else "illustrative sample",
        "run": summary.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in events],
    }
    return Response(
        json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-evidence.json"'},
    )


@router.get("/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    summary = await request.app.state.repository.get_run(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        after = int(last_event_id or 0)
    except ValueError:
        after = 0

    async def event_source() -> AsyncIterator[str]:
        cursor = after
        while True:
            if await request.is_disconnected():
                break
            events = await request.app.state.repository.wait_for_events(
                run_id, cursor, timeout=2.0
            )
            for event in events:
                cursor = event.id
                data = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
                yield f"id: {event.id}\nevent: {event.type}\ndata: {data}\n\n"
            current = await request.app.state.repository.require_run(run_id)
            if current.status in TERMINAL_RUN_STATUSES and not events:
                break
            if not events:
                yield ": heartbeat\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
