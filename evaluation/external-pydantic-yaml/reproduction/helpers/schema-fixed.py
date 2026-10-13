"""Fixed pydantic-yaml study: file handoffs, never a remote Sandbox provider.

Run with the reviewed BranchShift services/api on PYTHONPATH. The default advances
offline. Only --call-model enables ONE new local Nebius call per invocation.
No shell commands, repository code, GitHub APIs, or Sandbox APIs execute here.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import app
from app.domain.models import BranchResult, Citation, MigrationStrategy
from app.orchestrator.branch_runner import BranchRunner
from app.orchestrator.planner import MigrationPlanner, RepositoryEvidence, StrategyPlan
from app.providers.base import CommandResult, ProviderUnavailable, SandboxState
from app.providers.nebius import NebiusModelProvider
from app.providers.redaction import redact
from pydantic import BaseModel

REPO = "https://github.com/NowanIlfideme/pydantic-yaml"
COMMIT = "54ff4bad7bca758a9dd22a791b707a2b9c27159e"
MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
WORKDIR = "/tmp/branchshift-external-case/repo"
MAX_CALLS = 8
MAX_INPUT_BYTES = 150_000
MAX_OUTPUT_TOKENS = 16_384
SCOPE = "independent GitHub runner validation; not Nebius Sandbox evidence"
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def put(path: Path, data: bytes) -> None:
    """Create once; a replay may only reproduce identical bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ProtocolViolation(f"Immutable artifact changed: {path.name}") from None


def put_json(path: Path, value: Any) -> None:
    put(path, encoded(value))


def core_digest() -> str:
    # Freeze all Python implementation imports, not just the top-level prompts.
    root = Path(app.__file__).parent
    inventory = {str(path.relative_to(root)): digest(path.read_bytes())
                 for path in sorted(root.rglob("*.py"))}
    return digest(encoded(inventory))


def validate_baseline(evidence: RepositoryEvidence, context: dict[str, Any]) -> None:
    if str(evidence.repo_url).rstrip("/") != REPO or context.get("commit_sha") != COMMIT:
        raise ValueError("This helper only accepts the frozen pydantic-yaml commit")
    outcomes = evidence.test_outcomes or {}
    if (context.get("baseline_qualified") is not True
            or evidence.baseline_tests_passed is None
            or not evidence.test_contract_digest
            or len(outcomes) != evidence.baseline_tests_collected
            or sum(item == "passed" for item in outcomes.values())
            != evidence.baseline_tests_passed
            or any(item not in {"passed", "skipped"} for item in outcomes.values())
            or evidence.test_extras != ["pyyaml", "semver"]):
        raise ValueError("A passing unchanged baseline with complete outcome identities is required")


def initialize(session: Path, baseline: Path, citations_file: Path,
               candidate_constraints: Path) -> dict[str, Any]:
    evidence_data = (baseline / "repository-evidence.json").read_bytes()
    context_data = (baseline / "context.json").read_bytes()
    citation_data = citations_file.read_bytes()
    constraint_data = candidate_constraints.read_bytes()
    if "pydantic==2.12.5" not in constraint_data.decode().splitlines():
        raise ValueError("The frozen candidate constraints must include pydantic==2.12.5")
    evidence = RepositoryEvidence.model_validate_json(evidence_data)
    validate_baseline(evidence, json.loads(context_data))
    citations = [Citation.model_validate(item) for item in json.loads(citation_data)]
    if not citations:
        raise ValueError("Retained official citations are required; the helper does not fetch them")
    manifest = {
        "schema_version": 1, "evidence_scope": SCOPE, "commit_sha": COMMIT,
        "repository_evidence_sha256": digest(evidence_data),
        "context_sha256": digest(context_data), "citations_sha256": digest(citation_data),
        "candidate_constraints_sha256": digest(constraint_data),
        "implementation_digest": core_digest(), "model": MODEL, "thinking": True,
        "max_model_calls": MAX_CALLS, "max_input_bytes": MAX_INPUT_BYTES,
        "max_output_tokens": MAX_OUTPUT_TOKENS, "workdir": WORKDIR,
    }
    put(session / "repository-evidence.json", evidence_data)
    put(session / "context.json", context_data)
    put(session / "citations.json", citation_data)
    put(session / "candidate-constraints.txt", constraint_data)
    put_json(session / "manifest.json", manifest)
    return manifest


class Handoff(Exception):
    def __init__(self, path: Path, kind: str):
        self.path = path
        self.kind = kind


class ProtocolViolation(RuntimeError):
    """Never interpreted by the original planner as a repairable model response."""


class ReplayModel:
    """Replay saved responses; emit a request when no response exists.

    The original planner/runner owns prompts, schema validation and retry state.
    This adapter never synthesizes source replacements or repair diagnostics.
    """
    def __init__(self, session: Path, phase: str, *, provider: Any = None):
        self.session = session
        self.phase = phase
        self.provider = provider
        self.index = 0
        self.new_calls = 0

    async def complete_json(self, *, system: str, user: str,
                            schema: type[SchemaT]) -> SchemaT:
        self.index += 1
        payload = {"system": system, "user": user, "schema": schema.model_json_schema()}
        payload_bytes = encoded(payload)
        if len(payload_bytes) > MAX_INPUT_BYTES:
            raise ProtocolViolation("Complete system/user/schema exceeds the 150000-byte input cap")
        request_id = digest(encoded({"phase": self.phase, "index": self.index,
                                    "payload": payload}))
        folder = self.session / self.phase / f"model-{self.index:02d}"
        request = {"schema_version": 1, "request_id": request_id, "phase": self.phase,
                   "input_bytes": len(payload_bytes), "model": MODEL,
                   "thinking": True, "max_tokens": MAX_OUTPUT_TOKENS, **payload}
        put_json(folder / "request.json", request)
        response_path = folder / "response.json"
        if response_path.exists():
            try:
                saved = read_json(response_path)
            except ValueError as exc:
                raise ProtocolViolation("Stored model response is not valid JSON") from exc
            if saved["request_id"] != request_id:
                raise ProtocolViolation("Stored model response does not match its exact request")
        else:
            # A persisted attempt reserves budget even if interrupted or outcome is uncertain.
            existing = list((self.session / "calls").glob("*.json"))
            if any(read_json(item)["request_id"] == request_id for item in existing):
                raise ProtocolViolation("Model outcome is uncertain; inspect the retained attempt, never retry")
            if self.provider is None or self.new_calls:
                raise Handoff(folder / "request.json", "model")
            if len(existing) >= MAX_CALLS:
                raise ProtocolViolation("Eight remaining model calls already reserved; no further call is permitted")
            put_json(self.session / "calls" / f"{len(existing) + 1:02d}.json", {
                "request_id": request_id, "phase": self.phase,
                "input_bytes": len(payload_bytes), "status": "reserved-before-request",
                "started_at": datetime.now(UTC).isoformat(),
            })
            self.new_calls += 1
            before = dict(self.provider.usage)
            try:
                answer = await self.provider.complete_json(system=system, user=user, schema=schema)
                saved = {"request_id": request_id, "response": answer.model_dump(mode="json")}
            except Exception as exc:  # noqa: BLE001 -- retain failed-call evidence before propagating
                # Match known ProviderUnavailable text for the original invalid-schema repair path.
                saved = {"request_id": request_id, "error": redact(str(exc))[:1_000],
                         "error_type": type(exc).__name__}
            finally:
                after = dict(self.provider.usage)
            saved["usage"] = {
                key: after.get(key, 0) - before.get(key, 0)
                for key in ("requests", "input_tokens", "output_tokens", "responses_with_usage")
            }
            saved["usage"]["coverage"] = (
                "reported" if saved["usage"]["responses_with_usage"] == 1 else "unknown"
            )
            saved["finished_at"] = datetime.now(UTC).isoformat()
            put_json(response_path, saved)
        if "error" in saved:
            raise ProviderUnavailable(saved["error"])
        try:
            return schema.model_validate(saved["response"])
        except ValueError as exc:
            raise ProtocolViolation("Stored response no longer validates against its frozen schema") from exc


class OneRecordedCommand:
    """One exact local artifact, solely to reuse the existing validation parser/gates.

    There is no execution/transport implementation. The empty internal state ID
    satisfies the app interface only and is removed from every exported result.
    """
    def __init__(self, command: str, result: dict[str, Any], stdout: str, stderr: str):
        self.command, self.result = command, result
        self.stdout, self.stderr = stdout, stderr

    async def run(self, parent: SandboxState, command: str,
                  *, timeout_seconds: int) -> CommandResult:
        if command != self.command or timeout_seconds != 240:
            raise ValueError("Recorded result must match the exact original validation command")
        return CommandResult(SandboxState(""), self.stdout, self.stderr,
                             self.result["exit_code"], self.result["elapsed_seconds"])

    async def create_base(self, *args: Any, **kwargs: Any) -> SandboxState:
        raise AssertionError("Artifact parser cannot create or execute a baseline")

    async def read(self, *args: Any, **kwargs: Any) -> bytes:
        raise AssertionError("Artifact parser cannot read any execution environment")


class FileBranchRunner(BranchRunner):
    def __init__(self, model: ReplayModel, session: Path, phase: str):
        super().__init__(model, None, max_attempts=3, timeout_seconds=240)  # type: ignore[arg-type]
        self.session, self.phase, self.index = session, phase, 0

    async def validate_existing_patch(self, parent: SandboxState, strategy: MigrationStrategy,
                                      patch: str, **kwargs: Any) -> BranchResult:
        self.index += 1
        folder = self.session / self.phase / f"validation-{self.index:02d}"
        command = self._validation_command(
            WORKDIR, patch, expected_outcomes=kwargs.get("expected_outcomes"),
            test_extras=kwargs.get("test_extras"),
        )
        request = {
            "schema_version": 1, "evidence_scope": SCOPE, "phase": self.phase,
            "commit_sha": COMMIT, "strategy_id": strategy.id, "workdir": WORKDIR,
            "baseline_context_sha256": digest((self.session / "context.json").read_bytes()),
            "candidate_constraints_sha256": digest(
                (self.session / "candidate-constraints.txt").read_bytes()),
            "patch_sha256": digest(patch.encode()), "command_sha256": digest(command.encode()),
            "timeout_seconds": 240, "expected_pydantic": "2.12.5",
            "constraint_required": True, "clean_original_checkout_required": True,
        }
        put(folder / "candidate.patch", patch.encode())
        put(folder / "command.sh", command.encode())
        put_json(folder / "request.json", request)
        result_path = folder / "command-result.json"
        if not result_path.exists():
            raise Handoff(folder / "request.json", "validation")
        result = read_json(result_path)
        for field in ("commit_sha", "patch_sha256", "command_sha256", "baseline_context_sha256",
                      "candidate_constraints_sha256"):
            if result.get(field) != request[field]:
                raise ValueError(f"Runner receipt mismatches frozen {field}")
        if (result.get("executor") != "github-hosted-runner"
                or result.get("target_pydantic_version") != "2.12.5"
                or result.get("constraint_applied") is not True
                or result.get("started_from_clean_baseline") is not True
                or type(result.get("exit_code")) is not int
                or type(result.get("elapsed_seconds")) not in (int, float)
                or not 0 <= result["elapsed_seconds"] <= 300):
            raise ValueError("Incomplete fixed-case executor/environment receipt")
        logs = []
        for name in ("stdout", "stderr"):
            data = (folder / f"{name}.txt").read_bytes()
            if len(data) > 1_000_000 or digest(data) != result.get(f"{name}_sha256"):
                raise ValueError(f"Runner {name} is oversized or fails its recorded hash")
            logs.append(data.decode("utf-8"))
        parser = BranchRunner(self._model, OneRecordedCommand(command, result, *logs))
        branch = await parser.validate_existing_patch(parent, strategy, patch, **kwargs)
        if branch.status.value == "passed" and result.get("pydantic_version") != "2.12.5":
            raise ValueError("Passing result used a different Pydantic version than the fixed protocol")
        branch = branch.model_copy(update={"checkpoint_id": None})
        put_json(folder / "parsed-branch-result.json", branch.model_dump(mode="json"))
        return branch


async def advance(session: Path, phase: str, provider: Any = None) -> dict[str, Any]:
    manifest = read_json(session / "manifest.json")
    if manifest["implementation_digest"] != core_digest():
        raise ValueError("BranchShift implementation changed after this session was frozen")
    for filename, key in (("repository-evidence.json", "repository_evidence_sha256"),
                          ("context.json", "context_sha256"), ("citations.json", "citations_sha256"),
                          ("candidate-constraints.txt", "candidate_constraints_sha256")):
        if digest((session / filename).read_bytes()) != manifest[key]:
            raise ValueError(f"Frozen input changed: {filename}")
    evidence = RepositoryEvidence.model_validate_json((session / "repository-evidence.json").read_bytes())
    validate_baseline(evidence, read_json(session / "context.json"))
    citations = [Citation.model_validate(item) for item in read_json(session / "citations.json")]
    model = ReplayModel(session, phase, provider=provider)
    try:
        if phase == "plan":
            strategies = await MigrationPlanner(model).plan(evidence, citations)
            result = StrategyPlan(strategies=strategies).model_dump(mode="json")
        else:
            plan = StrategyPlan.model_validate(read_json(session / "plan" / "result.json"))
            strategies = MigrationPlanner._validate(plan.strategies, evidence, citations)
            strategy = next(item for item in strategies if item.id == phase)
            runner = FileBranchRunner(model, session, phase)
            outcome = await runner.run(SandboxState(""), strategy, evidence,
                                       workdir=WORKDIR, citations=citations)
            result = outcome.model_dump(mode="json")
        put_json(session / phase / "result.json", result)
        return {"status": "completed", "phase": phase, "evidence_scope": SCOPE,
                "path": str(session / phase / "result.json")}
    except Handoff as pending:
        return {"status": "awaiting-" + pending.kind, "path": str(pending.path),
                "evidence_scope": SCOPE}


def cost_receipt(session: Path) -> dict[str, Any]:
    responses = [read_json(path) for path in session.glob("*/model-*/response.json")]
    input_tokens = sum(item.get("usage", {}).get("input_tokens", 0) for item in responses)
    output_tokens = sum(item.get("usage", {}).get("output_tokens", 0) for item in responses)
    return {
        "reserved_calls": len(list((session / "calls").glob("*.json"))),
        "responses_retained": len(responses), "reported_input_tokens": input_tokens,
        "reported_output_tokens": output_tokens,
        "usage_complete": all(item.get("usage", {}).get("coverage") == "reported" for item in responses)
        and len(responses) == len(list((session / "calls").glob("*.json"))),
        "reported_token_estimate_usd": (input_tokens + 3 * output_tokens) / 1_000_000,
        "rate_basis": "parent-verified standard synchronous input $1/M, output $3/M",
        "maximum_derived_estimate_usd": 1.593216,
        "derivation": "8 * 150000 assumed maximum input tokens + 8 * 16384 output tokens",
        "limitations": "Byte-to-token bound assumption; tax unknown; not a billed-dollar hard limit. "
        "Unknown usage is not zero cost. Excludes runner, Sandbox, Tavily and other services.",
    }


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("session", type=Path)
    commands = cli.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("--baseline", type=Path, required=True)
    init.add_argument("--citations", type=Path, required=True)
    init.add_argument("--candidate-constraints", type=Path, required=True)
    step = commands.add_parser("advance")
    step.add_argument("phase", choices=["plan", "minimal", "compatibility", "refactor"])
    step.add_argument("--call-model", action="store_true", help="ONE billed Nebius call; default is offline")
    commands.add_parser("cost")
    args = cli.parse_args()
    args.session.mkdir(parents=True, exist_ok=True)
    lock = args.session / ".lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        if args.action == "init":
            output = initialize(args.session, args.baseline, args.citations,
                                args.candidate_constraints)
        elif args.action == "cost":
            output = cost_receipt(args.session)
        else:
            provider = None
            if args.call_model:
                # Do not load Settings/dotenv. Caller explicitly supplies only a process env key.
                provider = NebiusModelProvider(os.environ.get("NEBIUS_API_KEY", ""),
                                               "https://api.tokenfactory.nebius.com/v1/", MODEL,
                                               enable_thinking=True)
            output = asyncio.run(advance(args.session, args.phase, provider))
        print(json.dumps(output, indent=2))
    finally:
        os.close(descriptor)
        lock.unlink()


if __name__ == "__main__":
    main()
