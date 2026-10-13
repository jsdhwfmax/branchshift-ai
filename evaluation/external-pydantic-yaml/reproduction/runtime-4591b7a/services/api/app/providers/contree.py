from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from app.providers.base import CommandResult, ProviderUnavailable, SandboxState
from app.providers.redaction import redact

ResultT = TypeVar("ResultT")
SandboxOperation = Literal["image_use", "run", "read"]


class ContreeSandboxProvider:
    """Thin adapter for the 0.4 SDK's immutable image-state API.

    The raw SDK objects remain private. Orchestration sees opaque checkpoint
    identifiers and can only branch by executing from a known parent state.

    Usage version 1 counts adapter invocations of images.use, state.run and
    state.read, not the SDK's internal HTTP requests, polling or billable units.
    A run executes a shell command and produces a child state; it is not counted
    again as a separate spawn/fork. File writes and metrics commands inside that
    shell do not become separate SDK calls. No unsupported operation is inferred.
    Attempted means the SDK method was invoked; completed means it returned,
    including nonzero command exits (counted separately). Failed and cancelled
    calls have an unknown remote outcome and are never counted as completed.
    A terminal version-1 snapshot is settled only when attempted equals
    completed + failed + cancelled, both in total and for each operation.
    """

    def __init__(
        self, token: str, project_id: str, base_url: str,
        *, usage: dict[str, int] | None = None,
    ) -> None:
        if not token:
            raise ProviderUnavailable("NEBIUS_API_KEY is required for Contree")
        if not project_id:
            raise ProviderUnavailable("NEBIUS_PROJECT_ID is required for Contree")
        self._token = token
        self._project_id = project_id
        self._base_url = base_url
        self._sdk: Any = None
        self._states: dict[str, Any] = {}
        # Each live run supplies its own dictionary; no counters are process-global.
        # The marker distinguishes new observed zeros from uninstrumented old runs.
        self.usage = usage if usage is not None else {}
        self.usage["sandbox_usage_version"] = 1
        for operation in ("sdk_calls", "image_use", "run", "read"):
            for outcome in ("attempted", "completed", "failed", "cancelled"):
                self.usage.setdefault(f"sandbox_{operation}_{outcome}", 0)
        self.usage.setdefault("sandbox_run_exit_zero", 0)
        self.usage.setdefault("sandbox_run_exit_nonzero", 0)

    async def _observe(
        self, operation: SandboxOperation, invoke: Callable[[], Awaitable[ResultT]],
    ) -> ResultT:
        # No await occurs inside a counter update; sibling async branches cannot
        # interleave a read/modify/write on this run's dictionary.
        def record(outcome: str) -> None:
            self.usage[f"sandbox_{operation}_{outcome}"] += 1
            self.usage[f"sandbox_sdk_calls_{outcome}"] += 1

        record("attempted")
        try:
            result = await invoke()
        except asyncio.CancelledError:
            record("cancelled")
            raise
        except Exception:
            record("failed")
            raise
        record("completed")
        return result

    def _record_exit(self, exit_code: int) -> None:
        outcome = "zero" if exit_code == 0 else "nonzero"
        self.usage[f"sandbox_run_exit_{outcome}"] += 1

    async def __aenter__(self) -> ContreeSandboxProvider:
        try:
            from contree_sdk import Contree  # type: ignore[import-untyped]
            from contree_sdk.auth import IAMAuth  # type: ignore[import-untyped]
            from contree_sdk.config import ContreeConfig  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ProviderUnavailable("Install the 'contree' API extra") from exc
        config = ContreeConfig(
            auth=IAMAuth(
                token=self._token,
                project_id=self._project_id,
                base_url=self._base_url,
            ),
            transport_timeout=30.0,
            operation_run_timeout=300.0,
            operation_import_timeout=180.0,
        )
        self._sdk = Contree(config)
        await self._sdk.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._sdk is not None:
            await self._sdk.__aexit__(exc_type, exc, traceback)

    async def create_base(self, image: str, setup_command: str) -> SandboxState:
        if self._sdk is None:
            raise ProviderUnavailable("Contree provider must be used as an async context manager")
        base = await self._observe("image_use", lambda: self._sdk.images.use(image))
        prepared = await self._observe("run", lambda: base.run(
            shell=setup_command,
            timeout=300,
            disposable=False,
            truncate_output_at=32_000,
        ))
        exit_code = int(prepared.exit_code)
        self._record_exit(exit_code)
        if exit_code != 0:
            detail = redact(
                str(prepared.stdout) + "\n" + str(prepared.stderr),
                [self._token],
            )[-2_000:]
            raise ProviderUnavailable(f"Sandbox baseline setup failed: {detail}")
        state = SandboxState(checkpoint_id=str(prepared.uuid))
        self._states[state.checkpoint_id] = prepared
        return state

    async def run(
        self, parent: SandboxState, command: str, *, timeout_seconds: int
    ) -> CommandResult:
        raw_parent = self._states.get(parent.checkpoint_id)
        if raw_parent is None:
            raise ProviderUnavailable("Unknown or expired Sandbox checkpoint")
        started = time.monotonic()
        result = await self._observe("run", lambda: raw_parent.run(
            shell=command,
            timeout=timeout_seconds,
            disposable=False,
            truncate_output_at=32_000,
        ))
        exit_code = int(result.exit_code)
        self._record_exit(exit_code)
        state = SandboxState(checkpoint_id=str(result.uuid))
        self._states[state.checkpoint_id] = result
        return CommandResult(
            state=state,
            stdout=redact(str(result.stdout)),
            stderr=redact(str(result.stderr)),
            exit_code=exit_code,
            elapsed_seconds=time.monotonic() - started,
        )

    async def read(self, state: SandboxState, path: str) -> bytes:
        raw_state = self._states.get(state.checkpoint_id)
        if raw_state is None:
            raise ProviderUnavailable("Unknown or expired Sandbox checkpoint")
        content: bytes = await self._observe("read", lambda: raw_state.read(path))
        return content
