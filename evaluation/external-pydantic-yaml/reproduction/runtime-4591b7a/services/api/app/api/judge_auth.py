"""Optional private judge access, without changing run admission or its ledger."""
from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import secrets
from urllib.parse import urlsplit

from pydantic import SecretStr
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _one_header(scope: Scope, name: bytes) -> bytes | None:
    values = [value for key, value in scope["headers"] if key.lower() == name]
    if len(values) > 1:
        raise ValueError("Duplicate security header")
    return values[0] if values else None


def _same_origin_write(scope: Scope) -> bool:
    try:
        site = _one_header(scope, b"sec-fetch-site")
        if site is not None and site not in {b"same-origin", b"none"}:
            return False
        origin = _one_header(scope, b"origin")
        if origin is None:
            # Authenticated CLI clients have no browser Origin / Fetch Metadata.
            return True
        host = _one_header(scope, b"host")
        if host is None:
            return False
        origin_text, host_text = origin.decode("ascii"), host.decode("ascii")
        if any(c.isspace() or ord(c) < 32 for c in origin_text + host_text):
            return False
        source = urlsplit(origin_text)
        target = urlsplit(f"{source.scheme}://{host_text}")
        for url in (source, target):
            if (
                url.scheme not in {"http", "https"} or not url.hostname
                or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment
            ):
                return False
        if source.scheme == "http":
            # Public deployment terminates HTTPS at ingress while ASGI may see HTTP.
            # Match its Host, never attacker-supplied Forwarded / X-Forwarded-*.
            hostname = source.hostname or ""
            if hostname != "localhost":
                try:
                    if not ipaddress.ip_address(hostname).is_loopback:
                        return False
                except ValueError:
                    return False
        default_port = 443 if source.scheme == "https" else 80
        return (source.hostname, source.port if source.port is not None else default_port) == (
            target.hostname, target.port if target.port is not None else default_port,
        )
    except (UnicodeError, ValueError):
        return False


class JudgeAuthMiddleware:
    def __init__(self, app: ASGIApp, *, username: SecretStr, password: SecretStr) -> None:
        self.app = app
        # Fixed-length digests keep both comparisons constant-time even for UTF-8 input.
        self._username = hashlib.sha256(username.get_secret_value().encode("utf-8")).digest()
        self._password = hashlib.sha256(password.get_secret_value().encode("utf-8")).digest()

    def _authenticated(self, scope: Scope) -> bool:
        try:
            header = _one_header(scope, b"authorization")
            if header is None or len(header) > 4096:
                return False
            scheme, token = header.split(b" ", 1)
            if scheme.lower() != b"basic":
                return False
            decoded = base64.b64decode(token, validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (UnicodeError, ValueError, binascii.Error):
            return False
        username_matches = secrets.compare_digest(
            hashlib.sha256(username.encode("utf-8")).digest(), self._username,
        )
        password_matches = secrets.compare_digest(
            hashlib.sha256(password.encode("utf-8")).digest(), self._password,
        )
        return username_matches and password_matches

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # GET only: HEAD /api is not an existing health endpoint and is not exempt.
        if (
            scope["method"] == "GET" and scope["path"] == "/api"
            and scope.get("raw_path", b"/api") == b"/api"
        ):
            await self.app(scope, receive, send)
            return
        if not self._authenticated(scope):
            await JSONResponse(
                {"detail": "Authentication required."}, status_code=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="BranchShift judging", charset="UTF-8"',
                    "Cache-Control": "no-store",
                },
            )(scope, receive, send)
            return
        if scope["method"] not in {"GET", "HEAD", "OPTIONS"} and not _same_origin_write(scope):
            await JSONResponse(
                {"detail": "Cross-origin write requests are not allowed."}, status_code=403,
                headers={"Cache-Control": "no-store"},
            )(scope, receive, send)
            return

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    (name, value) for name, value in message.get("headers", [])
                    if name.lower() != b"cache-control"
                ] + [(b"cache-control", b"private, no-store")]
            await send(message)

        await self.app(scope, receive, private_send)
