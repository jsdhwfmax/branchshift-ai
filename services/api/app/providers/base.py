from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from app.domain.models import Citation

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ModelProvider(Protocol):
    async def complete_json(
        self, *, system: str, user: str, schema: type[SchemaT]
    ) -> SchemaT: ...


class ResearchProvider(Protocol):
    async def search_official(self, query: str, *, max_results: int = 5) -> list[Citation]: ...


@dataclass(frozen=True)
class SandboxState:
    checkpoint_id: str


@dataclass(frozen=True)
class CommandResult:
    state: SandboxState
    stdout: str
    stderr: str
    exit_code: int
    elapsed_seconds: float


class SandboxProvider(Protocol):
    async def create_base(self, image: str, setup_command: str) -> SandboxState: ...

    async def run(
        self, parent: SandboxState, command: str, *, timeout_seconds: int
    ) -> CommandResult: ...

    async def read(self, state: SandboxState, path: str) -> bytes: ...


class ProviderUnavailable(RuntimeError):
    pass


ProviderPayload = dict[str, Any]

