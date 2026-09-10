from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RunBodyLimitMiddleware:
    """Bound actual bytes before FastAPI's JSON parser or run admission executes."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http" or scope["method"] != "POST"
            or scope["path"].rstrip("/") != "/api/runs"
        ):
            await self.app(scope, receive, send)
            return
        # Content-Length may be absent or false. Never rely on it for the byte cap.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                response = JSONResponse(
                    {"detail": f"Run request body exceeds the {self.max_bytes}-byte limit."},
                    status_code=413,
                )
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        buffered = bytes(body)
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": buffered, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
