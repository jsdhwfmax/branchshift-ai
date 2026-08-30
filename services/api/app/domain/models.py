from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def http_url(value: str) -> HttpUrl:
    return _HTTP_URL_ADAPTER.validate_python(value)


class RunStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    PLANNING = "planning"
    BRANCHING = "branching"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BranchStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}


class CreateRunRequest(BaseModel):
    repo_url: HttpUrl
    target: Literal["pydantic-v2"] = "pydantic-v2"

    @field_validator("repo_url")
    @classmethod
    def public_github_https_only(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlparse(str(value))
        if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
            raise ValueError("Only public HTTPS GitHub repositories are supported")
        if parsed.username or parsed.password or parsed.port not in {None, 443}:
            raise ValueError("Credentials and custom ports are not allowed")
        if parsed.query or parsed.fragment:
            raise ValueError("Repository query strings and fragments are not allowed")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            raise ValueError("Use a repository root URL such as https://github.com/owner/repo")
        return value


class Citation(BaseModel):
    title: str
    url: HttpUrl
    evidence: str


class MigrationStrategy(BaseModel):
    id: Literal["minimal", "compatibility", "refactor"]
    title: str
    rationale: str
    ordered_steps: list[str]
    source_urls: list[HttpUrl]
    target_files: list[str] = Field(default_factory=list)


class BranchResult(BaseModel):
    strategy_id: Literal["minimal", "compatibility", "refactor"]
    status: BranchStatus
    tests_collected: int = Field(ge=0)
    tests_passed: int = Field(ge=0)
    tests_failed: int = Field(ge=0)
    pip_check_passed: bool
    lint_findings: int = Field(ge=0)
    changed_files: int = Field(ge=0)
    changed_lines: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    patch_applicable: bool = True
    patch: str | None = None

    @property
    def pass_ratio(self) -> float:
        if self.tests_collected == 0:
            return 0.0
        return self.tests_passed / self.tests_collected


class RunEvent(BaseModel):
    id: int
    run_id: str
    type: str
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    branch_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    id: str
    repo_url: HttpUrl
    target: Literal["pydantic-v2"] = "pydantic-v2"
    mode: Literal["mock", "live"] = "mock"
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    strategies: list[MigrationStrategy] = Field(default_factory=list)
    branches: list[BranchResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    winner_id: str | None = None
    patch: str | None = None
    report: str | None = None
    failure_reason: str | None = None


ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {RunStatus.PREPARING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.PREPARING: {RunStatus.PLANNING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.PLANNING: {RunStatus.BRANCHING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.BRANCHING: {RunStatus.EVALUATING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.EVALUATING: {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}


def assert_transition(current: RunStatus, next_status: RunStatus) -> None:
    if next_status not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid run transition: {current.value} -> {next_status.value}")
