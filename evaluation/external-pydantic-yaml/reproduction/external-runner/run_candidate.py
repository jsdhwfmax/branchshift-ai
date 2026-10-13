"""One fixed-case candidate on a fresh GitHub runner; no model or Nebius calls.

The request and original BranchShift command are reviewable evaluation inputs,
not a general-purpose remote execution API. Never run this on a developer host.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import platform
import re
import shutil
import tarfile

import run_comparator as protocol

WORKDIR = Path("/tmp/branchshift-external-case/repo")
SCOPE = "independent GitHub runner validation; not Nebius Sandbox evidence"
# Byte anchors from successful first baseline/codemod run 38331091063.
FROZEN = {
    "upstream-LICENSE": "97128793d72c6be0a21bdfd2405312d827dd87e0bbd8fc5c904ec2c37e7057e0",
    "baseline/context.json": "137eb03d02d03cd42e01a54da8792d7a3de6ea6522579cd6080871237c2e969b",
    "baseline/repository-evidence.json": "5f881e2f0c3eb2448e96465e8fb4c3d10e4465b9bcc3f4427953156da8ea1d53",
    "baseline/outcomes.json": "865571dab2827d5e840489fc446edae7b89be3a6183cc8db1fffe1a2990c8fd2",
    "baseline/test-contract-before.json": "424406d251c1824673472e0f01ad9a19da68a997b0ab57070604d8af57f8dc08",
    "baseline/source-files.json": "5a4e05c0d3f07dbb28dad3e9948bd581f6c4a90c6005ca3a2195bc47d10cfc4b",
    "candidate-environment/constraints.txt": "09cb776346095a5716b5ef8fb1b655bd9f7dafa615adaf7a6f0bdb2028abb007",
}


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"Missing, symlinked, or oversized input: {path.name}")
    return path.read_bytes()


def parse_constraints(raw: bytes) -> dict[str, str]:
    versions = {}
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)==([A-Za-z0-9.]+)", line)
        if not match or match[1] in versions:
            raise ValueError("Constraints must contain unique exact version pins only")
        versions[match[1]] = match[2]
    if versions.get("pydantic") != "2.12.5" or "pydantic-yaml" in versions:
        raise ValueError("Unexpected fixed-case Pydantic/runtime constraints")
    return versions


def validate_inputs(folder: Path, frozen: Path) -> tuple[dict, dict, dict]:
    for name, expected in FROZEN.items():
        if protocol.digest(read_bounded(frozen / name, 160_000)) != expected:
            raise ValueError(f"Frozen first-run evidence changed: {name}")
    context = json.loads((frozen / "baseline/context.json").read_bytes())
    if (context["commit_sha"] != protocol.UPSTREAM_SHA
            or context["baseline_qualified"] is not True
            or context["tests_collected"] != 15 or context["tests_passed"] != 14
            or context["tests_skipped"] != 1):
        raise ValueError("First-run baseline is not the qualified declared case")
    request = json.loads(read_bounded(folder / "request.json", 8_192))
    expected = {
        "schema_version": 1, "evidence_scope": SCOPE, "commit_sha": protocol.UPSTREAM_SHA,
        "workdir": str(WORKDIR), "baseline_context_sha256": FROZEN["baseline/context.json"],
        "candidate_constraints_sha256": FROZEN["candidate-environment/constraints.txt"],
        "timeout_seconds": 240, "expected_pydantic": "2.12.5", "constraint_required": True,
        "clean_original_checkout_required": True,
    }
    for name, value in expected.items():
        if request.get(name) != value or type(request.get(name)) is not type(value):
            raise ValueError(f"Unexpected request field: {name}")
    if (request.get("strategy_id") not in {"minimal", "compatibility", "refactor"}
            or request.get("phase") not in {"minimal", "compatibility", "refactor", "revalidation"}):
        raise ValueError("Unexpected candidate strategy/phase")
    if request["phase"] != "revalidation" and request["phase"] != request["strategy_id"]:
        raise ValueError("Candidate strategy must match its proposal phase")
    patch = read_bounded(folder / "candidate.patch", 120_000)
    command = read_bounded(folder / "command.sh", 200_000)
    if (protocol.digest(patch) != request.get("patch_sha256")
            or protocol.digest(command) != request.get("command_sha256")):
        raise ValueError("Request patch/command hash mismatch")
    if not patch or not command:
        raise ValueError("Candidate patch/command cannot be empty")
    patch.decode("utf-8")
    command_text = command.decode("utf-8")
    if (not command_text.startswith(f"set -eu; cd {WORKDIR}; ")
            or base64.b64encode(patch).decode("ascii") not in command_text
            or "--junitxml=/tmp/branchshift-pytest.xml" not in command_text):
        raise ValueError("Command is not bound to the fixed workdir/patch/test evidence")
    versions = parse_constraints((frozen / "candidate-environment/constraints.txt").read_bytes())
    return request, context, versions


def same_runtime(actual: dict, expected: dict) -> bool:
    return ("pydantic-yaml" in actual
            and {key: value for key, value in actual.items() if key != "pydantic-yaml"} == expected)


class CandidateRunner(protocol.Runner):
    def __init__(self, output: Path, folder: Path, frozen: Path):
        super().__init__(output)
        self.folder, self.frozen = folder, frozen
        self.report = {
            "schema_version": 1, "evidence_scope": SCOPE,
            "execution_environment": "github-hosted-runner", "not_a_nebius_sandbox_run": True,
            "upstream_commit": protocol.UPSTREAM_SHA, "status": "preparing", "stages": {},
            "checkpoint_id": None, "baseline_rerun": False, "codemod_rerun": False,
        }

    def execute(self) -> None:
        request, _, versions = validate_inputs(self.folder, self.frozen)
        result_dir = self.output / "validation"
        result_dir.mkdir()
        for name in ("request.json", "candidate.patch", "command.sh"):
            shutil.copyfile(self.folder / name, result_dir / name)
        shutil.copytree(self.frozen, self.output / "frozen")
        self.report.update(phase=request["phase"], strategy_id=request["strategy_id"],
                           request_sha256=protocol.digest((self.folder / "request.json").read_bytes()),
                           patch_sha256=request["patch_sha256"], command_sha256=request["command_sha256"],
                           baseline_context_sha256=request["baseline_context_sha256"],
                           candidate_constraints_sha256=request["candidate_constraints_sha256"])
        protocol.save(self.output / "runner.json", {
            "python": platform.python_version(), "platform": platform.platform(),
            "source_runner_keys": {key: os.environ.get(key) for key in (
                "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                "RUNNER_OS", "RUNNER_ARCH", "RUNNER_ENVIRONMENT", "ImageOS", "ImageVersion")},
            "image_uuid": None, "script_sha256": protocol.digest(Path(__file__).read_bytes()),
            "comparator_script_sha256": protocol.digest(Path(protocol.__file__).read_bytes()),
        })
        if WORKDIR.parent.exists():
            raise ValueError("Refusing to reuse or delete an existing candidate workdir")
        source = self.checkout("candidate-source", protocol.UPSTREAM_URL, protocol.UPSTREAM_SHA)
        WORKDIR.parent.mkdir()
        source.rename(WORKDIR)
        source = WORKDIR
        files = self.source_snapshot("original", source)
        if files != json.loads((self.frozen / "baseline/source-files.json").read_bytes()):
            raise ValueError("Clean checkout differs from actual baseline tracked bytes")
        contract = json.loads((self.frozen / "baseline/test-contract-before.json").read_bytes())
        if protocol.test_contract(source) != contract:
            raise ValueError("Clean checkout differs from original test/configuration contract")
        outcomes = json.loads((self.frozen / "baseline/outcomes.json").read_bytes())["test_outcomes"]
        constraints = self.output / "frozen/candidate-environment/constraints.txt"
        self.constraints_digest = protocol.digest(constraints.read_bytes())
        self.env["PIP_CONSTRAINT"] = str(constraints)
        py = self.venv("candidate-environment")
        self.run("candidate-environment/install-runtime", [str(py), "-m", "pip", "install",
                 "--no-cache-dir", "--report", str(self.output / "candidate-environment/install.json"),
                 "-r", str(constraints)], self.work)
        before_lock = self.lock("candidate-environment", py)
        if before_lock != versions:
            raise ValueError("Rebuilt runtime differs from the full first-run frozen constraint")
        (source / ".venv").symlink_to(py.parent.parent, target_is_directory=True)
        # Retain a canonical expected tree before executing any candidate source.
        # The real BranchShift script applies the patch itself; this index has no working-tree edits.
        expected_tree = self.patch_tree(source, result_dir / "candidate.patch", "expected")
        command = self.run("validation/original-command", ["/bin/sh", str(result_dir / "command.sh")],
                           source, timeout=request["timeout_seconds"], check=False)
        for stream in ("stdout", "stderr"):
            shutil.copyfile(result_dir / f"original-command.{stream}.txt", result_dir / f"{stream}.txt")
        actual_version = self.run("validation/pydantic-version", [str(py), "-c",
            "import importlib.metadata; print(importlib.metadata.version('pydantic'))"],
            self.work, timeout=15, check=False)
        observed = actual_version["stdout"].strip() if actual_version["exit_code"] == 0 else None
        # Receipt is retained even when the candidate's install/test step fails.
        receipt = {key: request[key] for key in ("commit_sha", "patch_sha256", "command_sha256",
                   "baseline_context_sha256", "candidate_constraints_sha256")}
        receipt.update(executor="github-hosted-runner", target_pydantic_version="2.12.5",
                       pydantic_version=observed, constraint_applied=True,
                       started_from_clean_baseline=True, exit_code=command["exit_code"],
                       elapsed_seconds=command["elapsed_seconds"],
                       timed_out=command["timed_out"], output_truncated=any(command["truncated"].values()),
                       **{f"{stream}_sha256": protocol.digest((result_dir / f"{stream}.txt").read_bytes())
                          for stream in ("stdout", "stderr")})
        if receipt["timed_out"] or receipt["output_truncated"]:
            receipt["exit_code"] = 124 if receipt["timed_out"] else 125
        protocol.save(result_dir / "command-result.json", receipt)
        # Preserve full original app files (when bounded), not only its tail diagnostics.
        for name in ("branchshift-pytest.xml", "branchshift-pytest.out", "branchshift-install.out",
                     "branchshift-pip.out", "branchshift-ruff.out"):
            path = Path("/tmp") / name
            if path.is_file() and not path.is_symlink():
                raw = path.read_bytes()
                (result_dir / name).write_bytes(raw[:protocol.LOG_LIMIT])
                protocol.save(result_dir / (name + ".receipt.json"), {
                    "bytes": len(raw), "sha256": protocol.digest(raw),
                    "retained_bytes": min(len(raw), protocol.LOG_LIMIT),
                    "truncated": len(raw) > protocol.LOG_LIMIT,
                })
        # Independent same-protocol comparator checks, not fabricated BranchResult fields.
        after_lock = self.lock("after-command", py)
        runtime_preserved = same_runtime(after_lock, versions)
        applied = self.current_tree(source, "observed-after-command") == expected_tree
        contract_preserved = protocol.test_contract(source) == contract
        protocol.save(result_dir / "application-check.json", {
            "expected_tree": expected_tree, "observed_exact_tree": applied,
            "test_contract_preserved": contract_preserved, "full_runtime_preserved": runtime_preserved,
        })
        if not contract_preserved:
            raise ValueError("Candidate changed original tests/pytest configuration; comparison blocked")
        result = self.evaluate("comparison", py, source, contract, outcomes)
        shutil.copyfile(self.output / "comparison/native-v2.json", result_dir / "native-v2.json")
        after_comparison = self.lock("after-comparison", py)
        final_tree = self.current_tree(source, "observed-after-comparison")
        self.report.update(status="candidate_validation_complete",
                           full_runtime_preserved=runtime_preserved and same_runtime(after_comparison, versions),
                           exact_candidate_tree_preserved=applied and final_tree == expected_tree,
                           original_command_exit_code=receipt["exit_code"],
                           candidate_native_migration_qualified=(result["qualified"]
                               and receipt["exit_code"] == 0 and runtime_preserved
                               and "\n__BRANCHSHIFT_INSTALL_EXIT=0\n" in command["stdout"]
                               and same_runtime(after_comparison, versions)
                               and applied and final_tree == expected_tree),
                           clean_revalidation=request["phase"] == "revalidation",
                           lint_scope_note="Original app uses ruff check .; independent comparison uses the same source-only scope as codemod.")
        protocol.save(self.output / "comparison/patch-stats.json", {
            "patch_sha256": request["patch_sha256"],
            "numstat": self.run("comparison/numstat", ["git", "diff", "--numstat"], source)["stdout"],
        })

    def patch_tree(self, source: Path, patch: Path, name: str) -> str:
        # Validate paths and original tests before making an alternate-index expected tree.
        stats = self.run(f"{name}/numstat", ["git", "apply", "--numstat", str(patch)], source)["stdout"]
        original = json.loads((self.frozen / "baseline/source-files.json").read_bytes())
        protected = json.loads((self.frozen / "baseline/test-contract-before.json").read_bytes())["files"]
        for line in stats.splitlines():
            added, removed, path = line.split("\t")
            if (not added.isdigit() or not removed.isdigit() or path not in original or path in protected
                    or (path != "pyproject.toml" and not path.endswith(".py"))):
                raise ValueError("Patch contains a new, binary, protected, or unsupported file")
        if not stats:
            raise ValueError("Candidate patch has no file changes")
        index = self.work / f"{name}.index"
        self.env["GIT_INDEX_FILE"] = str(index)
        try:
            self.run(f"{name}/read-tree", ["git", "read-tree", "HEAD"], source)
            self.run(f"{name}/apply-index", ["git", "apply", "--cached", str(patch)], source)
            tree = self.run(f"{name}/tree", ["git", "write-tree"], source)["stdout"].strip()
            raw = self.run(f"{name}/raw-diff", ["git", "diff", "--raw", "HEAD", tree], source)["stdout"]
            for line in raw.splitlines():
                metadata, _ = line.split("\t", 1)
                before_mode, after_mode, _, _, status = metadata.split()
                if before_mode != ":100644" or after_mode != "100644" or status != "M":
                    raise ValueError("Patch added/deleted/renamed a file or changed its mode")
            manifest = self.run(f"{name}/manifest", ["git", "show", tree + ":pyproject.toml"], source)["stdout"]
            original_manifest = (source / "pyproject.toml").read_text()
            if (protocol.digest(original_manifest.encode()) != protocol.MANIFEST_SHA
                    or manifest != original_manifest.replace('"pydantic>=1.8,<2"', '"pydantic>=2,<3"')):
                raise ValueError("Manifest must contain exactly the shared dependency-only upgrade")
            return tree
        finally:
            self.env.pop("GIT_INDEX_FILE", None)

    def current_tree(self, source: Path, name: str) -> str:
        self.env["GIT_INDEX_FILE"] = str(self.work / f"{name}.index")
        try:
            self.run(f"{name}/read-tree", ["git", "read-tree", "HEAD"], source)
            self.run(f"{name}/add-tracked", ["git", "add", "-u"], source)
            return self.run(f"{name}/tree", ["git", "write-tree"], source)["stdout"].strip()
        finally:
            self.env.pop("GIT_INDEX_FILE", None)


def main() -> int:
    protocol.guard_runner()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not output.is_relative_to(runner_temp) or output == runner_temp or output.exists():
        raise SystemExit("Output must be a fresh child of RUNNER_TEMP")
    runner = CandidateRunner(output, args.input.resolve(), args.frozen.resolve())
    try:
        runner.execute()
    except Exception as error:
        runner.report.update(status="execution_failed", failure_type=type(error).__name__,
                             failure_reason=str(error)[:1500])
    finally:
        protocol.save(output / "summary.json", runner.report)
        archive = output.parent / "external-pydantic-yaml-candidate.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for path in sorted(output.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    stream.add(path, arcname=path.relative_to(output), recursive=False)
        if archive.stat().st_size > protocol.ARCHIVE_LIMIT:
            runner.report.update(artifact_complete=False, artifact_error="Complete archive exceeded 5 MiB; only summary retained")
            protocol.save(output / "summary.json", runner.report)
            with tarfile.open(archive, "w:gz") as stream:
                stream.add(output / "summary.json", arcname="summary.json")
        receipt = {**runner.report, "artifact_bytes": archive.stat().st_size,
                   "artifact_sha256": protocol.digest(archive.read_bytes())}
        receipt["stages"] = {name: {key: value for key, value in stage.items() if key != "diagnostics"}
                             for name, stage in receipt["stages"].items()}
        summary = json.dumps(receipt, indent=2, sort_keys=True)
        print(summary)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
                stream.write("## Fixed external BranchShift candidate\n\nNo model or Nebius calls.\n\n```json\n" + summary + "\n```\n")
    return 0 if (runner.report["status"] == "candidate_validation_complete"
                 and runner.report.get("artifact_complete", True)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
