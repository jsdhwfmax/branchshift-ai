"""Fixed-case, no-user-secret GitHub-hosted evaluation. Never execute on a developer host."""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import tomllib
import xml.etree.ElementTree as ET

UPSTREAM_URL = "https://github.com/NowanIlfideme/pydantic-yaml"
UPSTREAM_SHA = "54ff4bad7bca758a9dd22a791b707a2b9c27159e"
TOOL_URL = "https://github.com/pydantic/bump-pydantic"
TOOL_SHA = "a111d4177405dbf61ef59035adaa0639b17b8718"
PYTHON = "3.12.15"
TEST_TREE = "src/pydantic_yaml/test"
MANIFEST_SHA = "3d46518b3d79bf4aa88ae54634fec25a1018387ecce56498a08bc3bb7392ae13"
LICENSE_SHA = "97128793d72c6be0a21bdfd2405312d827dd87e0bbd8fc5c904ec2c37e7057e0"
BOOTSTRAP = ["pip==25.2", "setuptools==80.9.0", "wheel==0.45.1",
             "setuptools-scm==8.3.1", "importlib-metadata==8.7.0"]
BASE_PINS = ["pydantic==1.10.24", "pytest==8.3.5", "PyYAML==6.0.2",
             "semver==3.0.4", "ruff==0.13.0", "typing-extensions==4.15.0"]
TOOL_PINS = ["hatchling==1.27.0", "typer==0.12.5", "click==8.1.8",
             "libcst==1.8.6", "rich==13.9.4", "typing-extensions==4.15.0"]
LOG_LIMIT = 131_072
ARCHIVE_LIMIT = 5 * 1024 * 1024
IGNORED = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def test_contract(root: Path) -> dict:
    """Same payload/identity algorithm as app.orchestrator.verification, no source imports."""
    files, total = {}, 0
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in IGNORED)
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root)
            protected = (any(part in {"test", "tests", "__tests__"} for part in relative.parts)
                         or name == "conftest.py" or name.startswith("test_")
                         or name.endswith("_test.py"))
            if not protected:
                continue
            if path.is_symlink():
                raise ValueError("Symlinked test files unsupported")
            data = path.read_bytes()
            total += len(data)
            if total > 2_000_000 or len(files) >= 500:
                raise ValueError("Test contract exceeds bounded evidence limits")
            files[relative.as_posix()] = digest(data)
    configuration = {}
    manifest = root / "pyproject.toml"
    if manifest.exists():
        configuration["pyproject.toml"] = tomllib.loads(manifest.read_text()).get("tool", {}).get("pytest", {})
    for name in ("pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg"):
        path = root / name
        if path.exists():
            parser = configparser.ConfigParser(interpolation=None)
            parser.read_string(path.read_text())
            configuration[name] = {section: dict(parser[section]) for section in parser.sections()
                                   if section in {"pytest", "tool:pytest"}}
    payload = {"files": files, "configuration": configuration}
    return {**payload, "digest": digest(json.dumps(payload, sort_keys=True).encode())}


def parse_junit(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 512_000:
        raise ValueError("Missing or oversized JUnit evidence")
    root = ET.parse(path).getroot()
    outcomes, issues, skips = {}, [], []
    for case in root.iter("testcase"):
        identity = case.get("classname", "") + "::" + case.get("name", "unknown")
        if identity in outcomes or len(outcomes) >= 500:
            raise ValueError("Duplicate or excessive testcase identity")
        issue = case.find("failure")
        if issue is None:
            issue = case.find("error")
        skip = case.find("skipped")
        outcomes[identity] = "failed" if issue is not None else "skipped" if skip is not None else "passed"
        if issue is not None:
            issues.append({"test": identity, "message": (issue.get("message") or "".join(issue.itertext()))[:1000]})
        if skip is not None:
            skips.append({"test": identity, "type": skip.get("type"), "message": skip.get("message"), "text": (skip.text or "")[:1000]})
    if not outcomes or len(json.dumps(outcomes, separators=(",", ":")).encode()) > 16_000:
        raise ValueError("Empty or excessive testcase evidence")
    return {"test_outcomes": outcomes, "tests_collected": len(outcomes),
            **{f"tests_{name}": list(outcomes.values()).count(name) for name in ("passed", "failed", "skipped")},
            "issues": issues, "skips_and_xfails": skips, "junit_sha256": digest(path.read_bytes())}


def outcomes_preserved(before: dict, after: dict) -> bool:
    return (set(before) == set(after) and all(
        (status == "passed" and after[key] == "passed") or (status == "skipped" and after[key] in {"passed", "skipped"})
        for key, status in before.items()))


def upgrade_manifest(path: Path) -> None:
    """The shared dependency-only step: same >=2,<3 manifest rule as BranchShift."""
    source = path.read_text()
    if digest(source.encode()) != MANIFEST_SHA or source.count('"pydantic>=1.8,<2"') != 1:
        raise ValueError("Manifest differs from the declared immutable baseline")
    replacement = source.replace('"pydantic>=1.8,<2"', '"pydantic>=2,<3"')
    expected = tomllib.loads(source)
    expected["project"]["dependencies"] = ["pydantic>=2,<3" if value == "pydantic>=1.8,<2" else value
                                              for value in expected["project"]["dependencies"]]
    if tomllib.loads(replacement) != expected:
        raise ValueError("Manifest rewrite touched unrelated fields")
    path.write_text(replacement)


class Runner:
    def __init__(self, output: Path):
        self.output = output
        self.work = output.parent / "work"
        self.work.mkdir(parents=True)
        self.output.mkdir(parents=True)
        home = self.work / "home"
        home.mkdir()
        temp = self.work / "tmp"
        temp.mkdir()
        # No ambient provider credentials or GitHub/Actions env is forwarded.
        # This is not a process-level security boundary from the runner itself.
        self.env = {"PATH": os.environ["PATH"], "HOME": str(home), "TMPDIR": str(temp),
                    "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "CI": "true",
                    "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_TERMINAL_PROMPT": "0"}
        self.commands = []
        self.constraints_digest = None
        self.report = {"schema_version": 1, "execution_environment": "github-hosted-runner",
                       "not_a_nebius_sandbox_run": True, "upstream_commit": UPSTREAM_SHA,
                       "codemod_commit": TOOL_SHA, "status": "preparing", "stages": {}}

    def run(self, name: str, args: list[str], cwd: Path, *, timeout: int = 180, check: bool = True) -> dict:
        start = time.monotonic()
        process = subprocess.Popen(args, cwd=cwd, env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        selector = selectors.DefaultSelector()
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        totals = {"stdout": 0, "stderr": 0}
        for stream, key in [(process.stdout, "stdout"), (process.stderr, "stderr")]:
            selector.register(stream, selectors.EVENT_READ, key)
        timed_out = False
        while selector.get_map():
            if time.monotonic() - start > timeout:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                # Bound even an inherited pipe from a subprocess which escaped the group.
                break
            for key, _ in selector.select(0.1):
                data = os.read(key.fileobj.fileno(), 65_536)
                if not data:
                    selector.unregister(key.fileobj)
                else:
                    totals[key.data] += len(data)
                    buffers[key.data].extend(data[:max(0, LOG_LIMIT - len(buffers[key.data]))])
        selector.close()
        process.wait(timeout=5)
        record = {"name": name, "argv": args, "cwd": str(cwd), "exit_code": process.returncode,
                  "timed_out": timed_out, "elapsed_seconds": time.monotonic() - start,
                  "bytes_observed": totals, "truncated": {key: total > LOG_LIMIT for key, total in totals.items()}}
        for key, value in buffers.items():
            file = self.output / f"{name}.{key}.txt"
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(value)
        self.commands.append(record)
        save(self.output / "commands.json", self.commands)
        result = {**record, **{key: value.decode("utf-8", "replace") for key, value in buffers.items()}}
        if check and (process.returncode or timed_out or any(record["truncated"].values())):
            raise RuntimeError(f"{name} failed, timed out or exceeded retained output limit; inspect command evidence")
        return result

    def checkout(self, name: str, url: str, commit: str) -> Path:
        path = self.work / name
        path.mkdir()
        self.run(f"{name}/git-init", ["git", "init", "-q"], path)
        self.run(f"{name}/git-remote", ["git", "remote", "add", "origin", url], path)
        self.run(f"{name}/git-fetch", ["git", "fetch", "--depth", "1", "origin", commit], path)
        self.run(f"{name}/git-checkout", ["git", "checkout", "--detach", commit], path)
        actual = self.run(f"{name}/git-head", ["git", "rev-parse", "HEAD"], path)["stdout"].strip()
        if actual != commit:
            raise ValueError("Source commit does not match the declared SHA")
        return path

    def source_snapshot(self, name: str, source: Path) -> dict:
        listing = self.run(f"{name}/tracked-files", ["git", "ls-files", "-z"], source)["stdout"]
        files = {}
        for relative in filter(None, listing.split("\0")):
            path = source / relative
            if path.is_symlink() or not path.is_file():
                raise ValueError("Tracked symlinks or missing files unsupported")
            files[relative] = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}
        if sum(item["bytes"] for item in files.values()) > 1_000_000:
            raise ValueError("Fixed source exceeds the declared bounded unit")
        save(self.output / name / "source-files.json", files)
        return files

    def venv(self, name: str) -> Path:
        path = self.work / (name + "-env")
        self.run(f"{name}/venv", [sys.executable, "-m", "venv", str(path)], self.work)
        py = path / "bin/python"
        self.run(f"{name}/bootstrap", [str(py), "-m", "pip", "install", "--no-cache-dir", "--report", str(self.output / name / "bootstrap-install.json"), *BOOTSTRAP], self.work)
        return py

    def lock(self, name: str, py: Path) -> dict:
        result = self.run(f"{name}/freeze", [str(py), "-m", "pip", "freeze", "--all"], self.work)
        (self.output / name / "pip-freeze.txt").write_text(result["stdout"])
        packages = json.loads(self.run(f"{name}/packages", [str(py), "-m", "pip", "list", "--format=json"], self.work)["stdout"])
        lock = {re.sub(r"[-_.]+", "-", item["name"].lower()): item["version"] for item in packages}
        save(self.output / name / "resolved-versions.json", lock)
        return lock

    def install_source(self, name: str, py: Path, source: Path) -> None:
        self.run(f"{name}/install-project", [str(py), "-m", "pip", "install", "--no-cache-dir",
                 "--no-build-isolation", "--no-deps", "--report", str(self.output / name / "project-install.json"),
                 "-e", ".[pyyaml,semver]"], source)

    def evaluate(self, name: str, py: Path, source: Path, baseline_contract: dict, expected: dict | None) -> dict:
        stage = self.output / name
        stage.mkdir(exist_ok=True, parents=True)
        before = test_contract(source)
        save(stage / "test-contract-before.json", before)
        if before != baseline_contract:
            raise ValueError("Original tests or pytest configuration were modified")
        pip = self.run(f"{name}/pip-check", [str(py), "-m", "pip", "check"], source, check=False)
        tests = self.run(f"{name}/pytest", [str(py), "-m", "pytest", "-q", TEST_TREE,
                         "-ra", "--tb=short", "--junitxml=" + str(stage / "junit.xml")], source, check=False)
        after = test_contract(source)
        save(stage / "test-contract-after.json", after)
        try:
            metrics = parse_junit(stage / "junit.xml")
        except (ValueError, ET.ParseError) as error:
            metrics = {"test_outcomes": {}, "tests_collected": 0, "tests_passed": 0,
                       "tests_failed": 0, "tests_skipped": 0, "evidence_error": str(error)}
        save(stage / "outcomes.json", metrics)
        preserved = expected is None or outcomes_preserved(expected, metrics["test_outcomes"])
        runtime = self.run(f"{name}/runtime", [str(py), "-c",
            "import json,platform,importlib.metadata as m;print(json.dumps({'python':platform.python_version(),'pydantic':m.version('pydantic'),'pytest':m.version('pytest'),'PyYAML':m.version('PyYAML'),'semver':m.version('semver')}))"], self.work)
        environment = json.loads(runtime["stdout"])
        save(stage / "environment.json", environment)
        structural_script = """import json, pydantic
result = {'installed_pydantic': pydantic.__version__, 'native_v2': False}
try:
    from pydantic_yaml import YamlModel
    result.update(subclass_of_native_BaseModel=issubclass(YamlModel, pydantic.BaseModel), model_fields=hasattr(YamlModel, 'model_fields'))
    result['native_v2'] = pydantic.__version__.split('.')[0] == '2' and result['subclass_of_native_BaseModel'] and result['model_fields']
except Exception as error:
    result.update(error_type=type(error).__name__, error=str(error)[:1000])
print(json.dumps(result))
"""
        probe = self.run(f"{name}/native-v2", [str(py), "-c", structural_script], source, check=False)
        native = {"native_v2": False, "evidence_error": "Structural probe did not return valid evidence"}
        if probe["exit_code"] == 0 and not probe["timed_out"]:
            try:
                native = json.loads(probe["stdout"])
            except ValueError:
                pass
        save(stage / "native-v2.json", native)
        lint = self.run(f"{name}/ruff", [str(py), "-m", "ruff", "check", "--output-format=json", "src/pydantic_yaml", "--exclude", TEST_TREE], source, check=False)
        try:
            lint_count = len(json.loads(lint["stdout"])) if lint["exit_code"] in (0, 1) else None
        except ValueError:
            lint_count = None
        final_contract = test_contract(source)
        save(stage / "test-contract-final.json", final_contract)
        valid_tests = (tests["exit_code"] == 0 and not tests["timed_out"] and metrics["tests_passed"] > 0
                       and metrics["tests_failed"] == 0 and before == after == final_contract and preserved and "evidence_error" not in metrics)
        result = {**{key: metrics[key] for key in ("tests_collected", "tests_passed", "tests_failed", "tests_skipped")},
                  "test_exit_code": tests["exit_code"], "pip_exit_code": pip["exit_code"],
                  "pip_check_passed": pip["exit_code"] == 0 and not pip["timed_out"],
                  "test_contract_preserved": before == after == final_contract == baseline_contract,
                  "test_outcomes_preserved": preserved if expected is not None else None,
                  "test_gate_passed": valid_tests, "native_v2": native.get("native_v2") is True,
                  "pydantic_version": environment["pydantic"], "lint_findings": lint_count,
                  "elapsed_seconds": tests["elapsed_seconds"], "checkpoint_id": None,
                  "candidate_constraints_sha256": self.constraints_digest,
                  "constraint_applied": expected is not None and self.constraints_digest is not None,
                  "target_pydantic_version": "1.10.24" if expected is None else "2.12.5",
                  "diagnostics": metrics.get("issues", [])[:3]}
        result["qualified"] = (valid_tests and result["pip_check_passed"] and
                               (environment["pydantic"] == "1.10.24" if expected is None else
                                environment["pydantic"] == "2.12.5" and result["native_v2"]))
        save(stage / "result.json", result)
        self.report["stages"][name] = result
        return {**result, "test_outcomes": metrics["test_outcomes"]}

    def repository_evidence(self, source: Path, files: dict, result: dict, contract: dict) -> None:
        python_files = sorted(name for name in files if name.endswith(".py"))[:200]
        manifests = [name for name in ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt") if name in files][:8]
        contents, total = {}, 0
        for name in [*manifests, *python_files]:
            raw = (source / name).read_bytes()
            if len(contents) >= 40:
                break
            if len(raw) > 25_000 or total + len(raw) > 100_000:
                if name in manifests:
                    raise ValueError("Manifest exceeds RepositoryEvidence limit")
                continue
            contents[name] = raw.decode("utf-8")
            total += len(raw)
        matches = []
        for name in python_files:
            for number, line in enumerate((source / name).read_text().splitlines(), 1):
                if re.search(r"pydantic|validator|parse_obj|parse_raw|\.dict\(", line):
                    matches.append(f"{name}:{number}:{line}")
        save(self.output / "baseline/repository-evidence.json", {"repo_url": UPSTREAM_URL,
             "dependency_manifests": manifests, "python_files": python_files, "symbol_matches": matches[:200],
             "file_contents": contents, "baseline_summary": f"{result['tests_collected']} tests collected; {result['tests_passed']} passed; {result['tests_failed']} failed",
             "baseline_tests_collected": result["tests_collected"], "baseline_tests_passed": result["tests_passed"],
             "test_outcomes": result["test_outcomes"], "test_extras": ["pyyaml", "semver"], "test_contract_digest": contract["digest"]})

    def execute(self) -> None:
        save(self.output / "protocol.json", {"python": PYTHON, "upstream": UPSTREAM_URL, "upstream_sha": UPSTREAM_SHA,
             "tool": TOOL_URL, "tool_sha": TOOL_SHA, "bootstrap_pins": BOOTSTRAP, "baseline_pins": BASE_PINS,
             "codemod_pins": TOOL_PINS, "candidate_pydantic_pin": "2.12.5", "manifest_requirement": ">=2,<3",
             "test_tree": TEST_TREE, "no_assertion_test_retained": "test_basic.py::test_readme",
             "xfail_retained": "test_secret_types.py::test_secret_types_roundtrippable",
             "adaptation": "GitHub-hosted filesystem copies and independently rebuilt locked venvs; not Nebius checkpoints"})
        save(self.output / "runner.json", {"python": platform.python_version(), "platform": platform.platform(),
             "source_runner_keys": {key: os.environ.get(key) for key in ["GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_ENVIRONMENT", "ImageOS", "ImageVersion"]},
             "image_uuid": None, "script_sha256": digest(Path(__file__).read_bytes())})
        source = self.checkout("baseline-source", UPSTREAM_URL, UPSTREAM_SHA)
        if digest((source / "pyproject.toml").read_bytes()) != MANIFEST_SHA or digest((source / "LICENSE").read_bytes()) != LICENSE_SHA:
            raise ValueError("Fixed upstream manifest/license fingerprint mismatch")
        shutil.copyfile(source / "LICENSE", self.output / "upstream-LICENSE")
        files = self.source_snapshot("baseline", source)
        contract = test_contract(source)
        py = self.venv("baseline")
        self.run("baseline/install", [str(py), "-m", "pip", "install", "--no-cache-dir", "--no-build-isolation",
                 "--report", str(self.output / "baseline/install.json"), "-e", ".[pyyaml,semver]", *BASE_PINS], source)
        baseline_lock = self.lock("baseline", py)
        result = self.evaluate("baseline", py, source, contract, None)
        after_files = self.source_snapshot("baseline-after", source)
        if after_files != files:
            raise ValueError("Baseline installation or tests changed tracked source bytes")
        self.repository_evidence(source, files, result, contract)
        save(self.output / "baseline/context.json", {"commit_sha": UPSTREAM_SHA, "baseline_qualified": result["qualified"],
             "test_contract_digest": contract["digest"], "tests_collected": result["tests_collected"], "tests_passed": result["tests_passed"],
             "tests_skipped": result["tests_skipped"], "execution_environment": "github-hosted-runner", "checkpoint_id": None})
        if not result["qualified"]:
            self.report["status"] = "baseline_failed_comparison_not_started"
            return
        # The original source tree is immutable; candidate changes occur in a separate checkout.
        candidate = self.checkout("codemod-source", UPSTREAM_URL, UPSTREAM_SHA)
        tool = self.checkout("tool-source", TOOL_URL, TOOL_SHA)
        shutil.copyfile(tool / "LICENSE.txt", self.output / "codemod-LICENSE")
        tool_py = self.venv("tool")
        self.run("tool/install-pins", [str(tool_py), "-m", "pip", "install", "--no-cache-dir", "--report", str(self.output / "tool/pins-install.json"), *TOOL_PINS], self.work)
        self.run("tool/install", [str(tool_py), "-m", "pip", "install", "--no-cache-dir", "--no-build-isolation", "--no-deps", "--report", str(self.output / "tool/source-install.json"), str(tool)], self.work)
        self.lock("tool", tool_py)
        codemod = self.run("codemod/command", [str(tool_py.parent / "bump-pydantic"), "src/pydantic_yaml"], candidate, check=False)
        log = candidate / "log.txt"
        codemod_errors = log.exists() and log.stat().st_size > 0
        if log.exists():
            (self.output / "codemod/codemod-error-log.txt").write_bytes(log.read_bytes()[:LOG_LIMIT])
        save(self.output / "codemod/command-status.json", {"exit_code": codemod["exit_code"], "timed_out": codemod["timed_out"], "error_log_nonempty": codemod_errors})
        before_restore = self.run("codemod/pre-restore-diff", ["git", "diff", "--no-ext-diff", "--binary"], candidate)
        (self.output / "codemod/pre-restore.patch").write_text(before_restore["stdout"])
        shutil.rmtree(candidate / TEST_TREE)
        shutil.copytree(source / TEST_TREE, candidate / TEST_TREE, ignore=shutil.ignore_patterns("__pycache__"))
        upgrade_manifest(candidate / "pyproject.toml")
        if test_contract(candidate) != contract:
            raise ValueError("Codemod changed a protected file outside the restored test tree")
        patch = self.run("codemod/diff", ["git", "diff", "--no-ext-diff", "--binary"], candidate)["stdout"]
        (self.output / "codemod/candidate.patch").write_text(patch)
        self.report["patch_sha256"] = digest(patch.encode())
        stats = self.run("codemod/numstat", ["git", "diff", "--numstat"], candidate)["stdout"]
        save(self.output / "codemod/patch-stats.json", {"sha256": self.report["patch_sha256"], "numstat": stats,
             "changed_files": len(stats.splitlines()), "changed_lines": sum(int(n) for line in stats.splitlines() for n in line.split('\t')[:2])})
        candidate_py = self.venv("codemod")
        locked = {name: version for name, version in baseline_lock.items() if name not in {"pydantic", "pydantic-yaml"}}
        lock_path = self.output / "codemod/shared-baseline-constraints.txt"
        lock_path.write_text("".join(f"{name}=={version}\n" for name, version in sorted(locked.items())))
        self.run("codemod/install-runtime", [str(candidate_py), "-m", "pip", "install", "--no-cache-dir", "--report", str(self.output / "codemod/runtime-install.json"), "-r", str(lock_path), "pydantic==2.12.5"], self.work)
        resolved_runtime = self.lock("candidate-environment", candidate_py)
        full_constraints = self.output / "candidate-environment/constraints.txt"
        full_constraints.write_text("".join(f"{name}=={version}\n" for name, version in sorted(resolved_runtime.items())))
        self.constraints_digest = digest(full_constraints.read_bytes())
        self.env["PIP_CONSTRAINT"] = str(full_constraints)
        save(self.output / "candidate-environment/constraint-receipt.json", {
            "candidate_constraints_sha256": self.constraints_digest,
            "target_pydantic_version": "2.12.5", "constraint_applied": True,
            "scope": "Every subsequent candidate and clean pip install uses this exact full environment constraint"})
        self.install_source("codemod", candidate_py, candidate)
        candidate_lock = self.lock("codemod", candidate_py)
        if any(candidate_lock.get(name) != version for name, version in locked.items()):
            raise ValueError("Candidate changed a shared baseline dependency")
        compared = self.evaluate("codemod", candidate_py, candidate, contract, result["test_outcomes"])
        clean = self.checkout("clean-source", UPSTREAM_URL, UPSTREAM_SHA)
        self.run("clean/apply-check", ["git", "apply", "--check", str(self.output / "codemod/candidate.patch")], clean)
        self.run("clean/apply", ["git", "apply", str(self.output / "codemod/candidate.patch")], clean)
        clean_patch = self.run("clean/exact-diff", ["git", "diff", "--no-ext-diff", "--binary"], clean)["stdout"]
        if clean_patch != patch:
            raise ValueError("Clean checkout does not reproduce the exact candidate patch")
        clean_py = self.venv("clean")
        clean_lock_path = self.output / "clean/resolved-requirements.txt"
        clean_lock_path.write_text("".join(f"{name}=={version}\n" for name, version in sorted(candidate_lock.items()) if name != "pydantic-yaml"))
        self.run("clean/install-runtime", [str(clean_py), "-m", "pip", "install", "--no-cache-dir", "--report", str(self.output / "clean/runtime-install.json"), "-r", str(clean_lock_path)], self.work)
        self.install_source("clean", clean_py, clean)
        if self.lock("clean", clean_py) != candidate_lock:
            raise ValueError("Clean revalidation environment differs from candidate")
        verified = self.evaluate("clean", clean_py, clean, contract, result["test_outcomes"])
        self.report["codemod_completed_without_errors"] = codemod["exit_code"] == 0 and not codemod["timed_out"] and not codemod_errors and not any(codemod["truncated"].values())
        self.report["status"] = "comparison_complete"
        self.report["codemod_native_migration_qualified"] = (compared["qualified"] and verified["qualified"] and self.report["codemod_completed_without_errors"])


def guard_runner() -> None:
    if (os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
        or os.environ.get("GITHUB_REPOSITORY") != "jsdhwfmax/branchshift-ai"
        or platform.system() != "Linux" or platform.python_version() != PYTHON):
        raise SystemExit("Refusing execution: only the declared public GitHub-hosted Linux runner and exact Python version are allowed")


def main() -> int:
    guard_runner()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not output.is_relative_to(runner_temp) or output == runner_temp or output.exists():
        raise SystemExit("Output must be a fresh child of RUNNER_TEMP")
    runner = Runner(output)
    try:
        runner.execute()
    except Exception as error:
        runner.report.update(status="execution_failed", failure_type=type(error).__name__, failure_reason=str(error)[:1500])
    finally:
        save(output / "summary.json", runner.report)
        archive = output.parent / "external-pydantic-yaml.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for path in sorted(output.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    stream.add(path, arcname=path.relative_to(output), recursive=False)
        if archive.stat().st_size > ARCHIVE_LIMIT:
            # Retain a truthful small failure receipt instead of exceeding artifact storage bounds.
            runner.report.update(artifact_complete=False, artifact_error="Complete archive exceeded 5 MiB; only summary retained")
            save(output / "summary.json", runner.report)
            with tarfile.open(archive, "w:gz") as stream:
                stream.add(output / "summary.json", arcname="summary.json")
        receipt = {**runner.report, "artifact_bytes": archive.stat().st_size, "artifact_sha256": digest(archive.read_bytes())}
        compact = {**receipt, "stages": {name: {key: value for key, value in stage.items() if key != "diagnostics"} for name, stage in receipt["stages"].items()}}
        summary = json.dumps(compact, indent=2, sort_keys=True)
        print(summary)
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            with open(step_summary, "a") as stream:
                stream.write("## Fixed external baseline and codemod\n\nNo Nebius run or model calls.\n\n```json\n" + summary + "\n```\n")
    return 0 if runner.report["status"] == "comparison_complete" and runner.report.get("artifact_complete", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
