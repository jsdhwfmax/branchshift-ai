"""Manual fixed-case control. Candidate execution is restricted to the declared GitHub runner."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "protocol"))
import run_candidate as candidate  # noqa: E402

protocol = candidate.protocol
AUTHORING_METHOD = "manual_codex_assisted"
MODEL_CALLS_SCOPE = "evaluated_nebius_provider_only"
PROTOCOL_SHA256 = {
    "run_candidate.py": "e4759438d5b2b962abbb2999b032388b28b4a47e0f38ebf76395bbdfe5aad456",
    "run_comparator.py": "607953f48e8beb23e0795ecf252e1a2d4fd39fe8b775431a630f06a04c50eb54",
}


def read_json(path: Path) -> dict:
    value = json.loads(candidate.read_bounded(path, 100_000))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def manual_metadata(request: dict, qualified: Path | None) -> dict:
    if request.get("authoring_method") != AUTHORING_METHOD:
        raise ValueError("Explicit manual_codex_assisted authoring is required")
    if type(request.get("model_calls")) is not int or request["model_calls"] != 0:
        raise ValueError("Manual control must declare exactly zero model calls")
    iteration = request.get("manual_iteration")
    if type(iteration) is not int or not 1 <= iteration <= 4:
        raise ValueError("manual_iteration must be between 1 and 4")
    role = "clean_repeat" if request.get("phase") == "revalidation" else "candidate"
    metadata = {
        "authoring_method": AUTHORING_METHOD, "model_calls": 0,
        "model_calls_scope": MODEL_CALLS_SCOPE,
        "manual_iteration": iteration, "manual_role": role, "manual_metadata_validated": True,
        "prior_qualified_receipt": None,
    }
    if role == "candidate":
        if qualified is not None:
            raise ValueError("A prior qualified receipt is only used for a clean repeat")
        return metadata
    if qualified is None:
        raise ValueError("Clean repeat requires the prior qualified manual candidate receipt")
    summary_path = qualified / "summary.json"
    check_path = qualified / "validation/application-check.json"
    previous, check = read_json(summary_path), read_json(check_path)
    expected = {
        "authoring_method": AUTHORING_METHOD, "model_calls": 0,
        "model_calls_scope": MODEL_CALLS_SCOPE,
        "manual_iteration": iteration, "manual_role": "candidate",
        "manual_metadata_validated": True, "status": "candidate_validation_complete",
        "execution_environment": "github-hosted-runner",
        "upstream_commit": protocol.UPSTREAM_SHA,
        "candidate_native_migration_qualified": True,
        "patch_sha256": request["patch_sha256"],
        "command_sha256": request["command_sha256"],
        "baseline_context_sha256": request["baseline_context_sha256"],
        "candidate_constraints_sha256": request["candidate_constraints_sha256"],
    }
    if any(previous.get(key) != value or type(previous.get(key)) is not type(value)
           for key, value in expected.items()):
        raise ValueError("Clean repeat must use the same qualified manual patch and command")
    if (previous.get("manual_original_command_gate", {}).get("passed") is not True
            or not application_qualified(check)):
        raise ValueError("Prior command/application checks did not qualify")
    metadata["prior_qualified_receipt"] = {
        "summary_sha256": protocol.digest(summary_path.read_bytes()),
        "application_check_sha256": protocol.digest(check_path.read_bytes()),
    }
    return metadata


def application_qualified(check: dict) -> bool:
    return all(check.get(key) is True for key in (
        "observed_exact_tree", "test_contract_preserved", "full_runtime_preserved"
    ))


def original_command_gate(stdout: str) -> dict:
    names = (
        "TEST_EXIT", "PIP_EXIT", "INSTALL_EXIT", "TESTS_COLLECTED", "TESTS_PASSED",
        "TESTS_FAILED", "TESTS_SKIPPED", "TEST_OUTCOMES_PRESERVED", "PYDANTIC_MAJOR",
    )
    observed = {}
    for name in names:
        values = re.findall(rf"^__BRANCHSHIFT_{name}=(-?\d+)$", stdout, re.MULTILINE)
        observed[name] = int(values[0]) if len(values) == 1 else None
    passed = (
        all(observed[name] == 0 for name in ("TEST_EXIT", "PIP_EXIT", "INSTALL_EXIT"))
        and observed["TESTS_COLLECTED"] == 15
        and observed["TESTS_PASSED"] in (14, 15)
        and observed["TESTS_SKIPPED"] in (0, 1)
        and observed["TESTS_PASSED"] + observed["TESTS_SKIPPED"] == 15
        and observed["TESTS_FAILED"] == 0
        and observed["TEST_OUTCOMES_PRESERVED"] == 1
        and observed["PYDANTIC_MAJOR"] == 2
    )
    return {
        "passed": passed, "markers": observed,
        "scope": "Original command markers plus the unchanged independent suite/native gate; "
                 "lint remains recorded, not an added migration gate",
    }


def validate_inputs(folder: Path, frozen: Path, qualified: Path | None) -> tuple[dict, dict]:
    for name, expected in PROTOCOL_SHA256.items():
        if protocol.digest((HERE / "protocol" / name).read_bytes()) != expected:
            raise ValueError(f"Frozen comparison protocol changed: {name}")
    request, _, _ = candidate.validate_inputs(folder, frozen)
    return request, manual_metadata(request, qualified)


class ManualRunner(candidate.CandidateRunner):
    def __init__(self, output: Path, folder: Path, frozen: Path, qualified: Path | None):
        super().__init__(output, folder, frozen)
        self.qualified = qualified
        self.report.update(authoring_method=AUTHORING_METHOD, model_calls=0,
                           model_calls_scope=MODEL_CALLS_SCOPE,
                           manual_metadata_validated=False)

    def execute(self) -> None:
        _, metadata = validate_inputs(self.folder, self.frozen, self.qualified)
        self.report.update(metadata)
        protocol.save(self.output / "manual-harness.json", {
            **metadata, "harness_sha256": protocol.digest(Path(__file__).read_bytes()),
            "protocol_sha256": PROTOCOL_SHA256,
            "source_commit": "58ff031d8208c3e54511d26fa3c64ba4e1b0616e",
            "iteration_limit": 4, "clean_repeat_limit": 1,
            "counting_owner": "Human-controlled execution ledger; no automatic retries",
        })
        super().execute()


def finish(runner: ManualRunner) -> Path:
    output = runner.output
    check_path = output / "validation/application-check.json"
    if not check_path.exists():
        protocol.save(check_path, {
            "status": "not_completed", "observed_exact_tree": None,
            "test_contract_preserved": None, "full_runtime_preserved": None,
            "reason": "Execution ended before the original application checks completed",
        })
    stdout = output / "validation/stdout.txt"
    gate = original_command_gate(stdout.read_text(errors="replace") if stdout.is_file() else "")
    original_qualified = runner.report.get("candidate_native_migration_qualified") is True
    runner.report.update(
        protocol_candidate_native_migration_qualified=original_qualified,
        manual_original_command_gate=gate,
        candidate_native_migration_qualified=(
            original_qualified and gate["passed"] and application_qualified(read_json(check_path))
        ),
    )
    protocol.save(output / "validation/manual-original-command-gate.json", gate)
    protocol.save(output / "summary.json", runner.report)
    archive = output.parent / "manual-native-control.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for path in sorted(output.rglob("*")):
            if path.is_file() and not path.is_symlink():
                stream.add(path, arcname=path.relative_to(output), recursive=False)
    if archive.stat().st_size > protocol.ARCHIVE_LIMIT:
        runner.report.update(
            artifact_complete=False, candidate_native_migration_qualified=False,
            artifact_error="Complete evidence exceeds 5 MiB; failure receipts only",
        )
        protocol.save(output / "summary.json", runner.report)
        with tarfile.open(archive, "w:gz") as stream:
            for path in (output / "summary.json", check_path,
                         output / "validation/manual-original-command-gate.json"):
                stream.add(path, arcname=path.relative_to(output), recursive=False)
    receipt = {
        **runner.report, "artifact_bytes": archive.stat().st_size,
        "artifact_sha256": protocol.digest(archive.read_bytes()),
    }
    summary = json.dumps(receipt, indent=2, sort_keys=True)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write("## Manual native-v2 control\n\nAuthored directly with Codex; "
                         "zero evaluated Nebius/Nemotron API calls. Independent GitHub runner, "
                         "not a Nebius Sandbox run."
                         "\n\n```json\n" + summary + "\n```\n")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--frozen", type=Path, default=HERE / "frozen")
    parser.add_argument("--qualified-control", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        request, metadata = validate_inputs(args.input, args.frozen, args.qualified_control)
        print(json.dumps({**metadata, "patch_sha256": request["patch_sha256"],
                          "check_only": True, "candidate_executed": False}, indent=2))
        return 0
    protocol.guard_runner()
    if (os.environ.get("GITHUB_REF") != "refs/heads/evaluation/manual-native-20261013"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise SystemExit("Only the dedicated branch's first workflow attempt may execute")
    if args.output is None:
        raise SystemExit("Execution requires --output")
    output = args.output.resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not output.is_relative_to(runner_temp) or output == runner_temp or output.exists():
        raise SystemExit("Output must be a fresh child of RUNNER_TEMP")
    runner = ManualRunner(
        output, args.input.resolve(), args.frozen.resolve(), args.qualified_control
    )
    try:
        runner.execute()
    except Exception as error:
        runner.report.update(status="execution_failed", failure_type=type(error).__name__,
                             failure_reason=str(error)[:1500])
    finally:
        finish(runner)
    return 0 if (runner.report["status"] == "candidate_validation_complete"
                 and runner.report.get("artifact_complete", True)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
