from __future__ import annotations

import time
from typing import Any

from app.providers.base import CommandResult, ProviderUnavailable, SandboxState
from app.providers.redaction import redact


class ContreeSandboxProvider:
    """Thin adapter for the 0.4 SDK's immutable image-state API.

    The raw SDK objects remain private. Orchestration sees opaque checkpoint
    identifiers and can only branch by executing from a known parent state.
    """

    def __init__(self, token: str, base_url: str) -> None:
        if not token:
            raise ProviderUnavailable("NEBIUS_API_KEY is required for Contree")
        self._token = token
        self._base_url = base_url
        self._api_client: Any = None
        self._sdk: Any = None
        self._sdk_owns_transport = False
        self._states: dict[str, Any] = {}

    async def __aenter__(self) -> ContreeSandboxProvider:
        try:
            from contree_client.httpx import ContreeAsyncClient
            from contree_client.runtime import RetryPolicy
            from contree_sdk import Contree  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ProviderUnavailable("Install the 'contree' API extra") from exc
        api_client = ContreeAsyncClient(
            self._token,
            base_url=self._base_url,
            timeout=30.0,
            retry=RetryPolicy(max_attempts=3),
        )
        await api_client.__aenter__()
        try:
            # Current docs/main branch: transport is constructed explicitly.
            self._sdk = Contree(api_client)
            self._api_client = api_client
        except AttributeError:
            # PyPI 0.4.0.dev5 still ships the legacy convenience constructor.
            await api_client.__aexit__(None, None, None)
            self._sdk = Contree(token=self._token, base_url=self._base_url)
            await self._sdk.__aenter__()
            self._sdk_owns_transport = True
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._sdk_owns_transport and self._sdk is not None:
            await self._sdk.__aexit__(exc_type, exc, traceback)
        elif self._api_client is not None:
            await self._api_client.__aexit__(exc_type, exc, traceback)

    async def create_base(self, image: str, setup_command: str) -> SandboxState:
        if self._sdk is None:
            raise ProviderUnavailable("Contree provider must be used as an async context manager")
        base = await self._sdk.images.use(image)
        prepared = await base.run(
            shell=setup_command,
            disposable=False,
            truncate_output_at=32_000,
        )
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
        result = await raw_parent.run(
            shell=command,
            timeout=timeout_seconds,
            disposable=False,
            truncate_output_at=32_000,
        )
        state = SandboxState(checkpoint_id=str(result.uuid))
        self._states[state.checkpoint_id] = result
        return CommandResult(
            state=state,
            stdout=redact(str(result.stdout)),
            stderr=redact(str(result.stderr)),
            exit_code=int(result.exit_code),
            elapsed_seconds=time.monotonic() - started,
        )

    async def read(self, state: SandboxState, path: str) -> bytes:
        raw_state = self._states.get(state.checkpoint_id)
        if raw_state is None:
            raise ProviderUnavailable("Unknown or expired Sandbox checkpoint")
        return await raw_state.read(path)
