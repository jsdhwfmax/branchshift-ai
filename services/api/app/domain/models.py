from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, TypeAdapter, field_validator

from app.orchestrator.behavior_probes import (
    BehaviorProbeComparison,
    BehaviorProbeResults,
    BehaviorProbeSuite,
)


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


def validate_project_path(value: str) -> str:
    if (
        not 1 <= len(value) <= 200
        or not re.fullmatch(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", value)
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise ValueError(
            "Project path must be a repository-relative path of at most 200 characters, "
            "using letters, digits, dots, underscores and hyphens without empty or dot segments"
        )
    return value


ProjectPath = Annotated[
    str, Field(min_length=1, max_length=200), AfterValidator(validate_project_path)
]
CommitSHA = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
PackageExtra = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$")]


class CreateRunRequest(BaseModel):
    repo_url: HttpUrl
    target: Literal["pydantic-v2"] = "pydantic-v2"
    project_path: ProjectPath | None = None
    baseline_ref: CommitSHA | None = None
    test_extras: list[PackageExtra] = Field(default_factory=lambda: ["test"], max_length=8)
    behavior_probes: BehaviorProbeSuite | None = None

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
    ordered_steps: list[str] = Field(min_length=1, max_length=8)
    source_urls: list[HttpUrl]
    target_files: list[str] = Field(min_length=1, max_length=40)


class BranchResult(BaseModel):
    strategy_id: Literal["minimal", "compatibility", "refactor"]
    status: BranchStatus
    tests_collected: int = Field(ge=0)
    tests_passed: int = Field(ge=0)
    tests_failed: int = Field(ge=0)
    tests_skipped: int | None = Field(default=None, ge=0)
    test_outcomes_preserved: bool | None = None
    pip_check_passed: bool
    lint_findings: int = Field(ge=0)
    changed_files: int = Field(ge=0)
    changed_lines: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    patch_applicable: bool = True
    patch: str | None = None
    diagnostics: str | None = Field(default=None, max_length=4_000)
    failure_reason: str | None = Field(default=None, max_length=500)
    pydantic_major: int | None = Field(default=None, ge=0)
    test_exit_code: int | None = None
    pip_exit_code: int | None = None
    test_contract_preserved: bool | None = None
    checkpoint_id: str | None = None
    behavior_probe_results: BehaviorProbeResults | None = None
    behavior_probe_comparison: BehaviorProbeComparison | None = None
    behavior_probe_error: str | None = Field(default=None, max_length=500)

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
    project_path: ProjectPath | None = None
    baseline_ref: CommitSHA | None = None
    test_extras: list[PackageExtra] = Field(default_factory=lambda: ["test"], max_length=8)
    behavior_probes: BehaviorProbeSuite | None = None
    baseline_probe_results: BehaviorProbeResults | None = None
    baseline_probe_error: str | None = Field(default=None, max_length=500)
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
    baseline_commit_sha: str | None = None
    baseline_checkpoint_id: str | None = None
    baseline_tests_collected: int | None = Field(default=None, ge=1)
    baseline_tests_passed: int | None = Field(default=None, ge=1)
    baseline_tests_skipped: int | None = Field(default=None, ge=0)
    model_id: str | None = None
    provider_usage: dict[str, int] = Field(default_factory=dict)
    baseline_test_contract_digest: str | None = None
    revalidated_checkpoint_id: str | None = None
    revalidation: BranchResult | None = None
    orchestrator_revision: str | None = None
    orchestrator_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    orchestrator_dirty: bool | None = None
    runtime_config_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RunListItem(BaseModel):
    """Small saved-run index; full evidence stays on the individual run."""

    id: str
    repo_url: HttpUrl
    project_path: ProjectPath | None = None
    mode: Literal["mock", "live"]
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    winner_id: str | None = None
    baseline_tests_collected: int | None = Field(default=None, ge=1)


class RunList(BaseModel):
    runs: list[RunListItem]
    limit: int = Field(ge=1, le=20)


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
