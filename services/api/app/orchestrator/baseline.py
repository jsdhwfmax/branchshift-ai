from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath

from pydantic import HttpUrl

from app.domain.models import CreateRunRequest, validate_project_path
from app.orchestrator.planner import RepositoryEvidence
from app.orchestrator.repository_size import (
    DEFAULT_MAX_REPOSITORY_BYTES,
    repository_size_guard_command,
)
from app.orchestrator.verification import (
    junit_metrics_command,
    marker_int,
    marker_text,
    runtime_version_command,
    test_contract_command,
)
from app.providers.base import SandboxProvider, SandboxState

CONTROLLED_REPOSITORY = "https://github.com/jsdhwfmax/branchshift-ai"
REPOSITORY_ROOT = "/workspace/repo"


class BaselineError(RuntimeError):
    pass


@dataclass(frozen=True)
class BaselineOutcome:
    state: SandboxState
    evidence: RepositoryEvidence
    commit_sha: str
    tests_collected: int
    tests_passed: int


class BaselineRunner:
    def __init__(
        self, sandbox: SandboxProvider, *, timeout_seconds: int = 300,
        max_repository_bytes: int = DEFAULT_MAX_REPOSITORY_BYTES,
    ) -> None:
        if type(max_repository_bytes) is not int or max_repository_bytes < 1:
            raise ValueError("MAX_REPOSITORY_BYTES must be a positive integer")
        self._sandbox = sandbox
        self._timeout_seconds = timeout_seconds
        self._max_repository_bytes = max_repository_bytes

    async def prepare(
        self,
        image: str,
        repo_url: HttpUrl | str,
        *,
        project_path: str | None = None,
    ) -> BaselineOutcome:
        request = CreateRunRequest.model_validate(
            {"repo_url": repo_url, "project_path": project_path}
        )
        validated_url = request.repo_url
        workdir = repository_workdir(validated_url, request.project_path)
        base = await self._sandbox.create_base(
            image,
            build_setup_command(validated_url, workdir, self._max_repository_bytes),
        )
        checked = await self._sandbox.run(
            base,
            build_baseline_command(workdir),
            timeout_seconds=self._timeout_seconds,
        )
        if checked.exit_code != 0:
            raise BaselineError(
                "Baseline command could not complete safely: "
                + (checked.stdout + "\n" + checked.stderr)[-1_500:]
            )
        test_exit = marker_int(checked.stdout, "TEST_EXIT")
        collected = marker_int(checked.stdout, "TESTS_COLLECTED")
        passed = marker_int(checked.stdout, "TESTS_PASSED")
        failed = marker_int(checked.stdout, "TESTS_FAILED")
        if test_exit != 0 or failed != 0 or passed <= 0 or collected < passed:
            raise BaselineError(
                "Repository baseline must pass at least one test: " + checked.stdout[-1_500:]
            )
        commit_sha = _marker_text(checked.stdout, "COMMIT")
        if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise BaselineError("Sandbox did not return a valid pinned commit SHA")
        python_files = _section(checked.stdout, "PYTHON_FILES")[:200]
        manifests = _section(checked.stdout, "MANIFESTS")[:8]
        matches = _section(checked.stdout, "SYMBOL_MATCHES")[:200]
        if not python_files or not manifests:
            raise BaselineError("Only Python repositories with a supported manifest are accepted")
        if marker_int(checked.stdout, "PYDANTIC_MAJOR") != 1:
            raise BaselineError("The baseline must use Pydantic v1 before migration")
        contract = marker_text(checked.stdout, "CONTRACT_BEFORE")
        if (
            not re.fullmatch(r"[0-9a-f]{64}", contract)
            or marker_text(checked.stdout, "CONTRACT_AFTER") != contract
        ):
            raise BaselineError("Baseline tests changed their immutable test contract")
        file_contents: dict[str, str] = {}
        total_bytes = 0
        for name in [*manifests, *python_files]:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
                raise BaselineError("Repository evidence contains an unsafe file path")
            if len(file_contents) >= 40:
                break
            raw = await self._sandbox.read(checked.state, f"{workdir}/{name}")
            if len(raw) > 25_000 or total_bytes + len(raw) > 100_000:
                if name in manifests:
                    raise BaselineError("Dependency manifest exceeds the source evidence limit")
                continue
            try:
                file_contents[name] = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise BaselineError("Only UTF-8 repository source files are supported") from exc
            total_bytes += len(raw)
        evidence = RepositoryEvidence(
            repo_url=validated_url,
            dependency_manifests=manifests,
            python_files=python_files,
            symbol_matches=matches,
            baseline_summary=f"{collected} tests collected; {passed} passed; {failed} failed",
            baseline_tests_collected=collected,
            file_contents=file_contents,
            test_contract_digest=contract,
        )
        return BaselineOutcome(
            state=checked.state,
            evidence=evidence,
            commit_sha=commit_sha,
            tests_collected=collected,
            tests_passed=passed,
        )


def repository_workdir(repo_url: HttpUrl, project_path: str | None = None) -> str:
    if project_path is not None:
        return f"{REPOSITORY_ROOT}/{validate_project_path(project_path)}"
    normalized = str(repo_url).removesuffix("/").removesuffix(".git")
    if normalized == CONTROLLED_REPOSITORY:
        return f"{REPOSITORY_ROOT}/fixtures/pydantic-v1-app"
    return REPOSITORY_ROOT


def build_setup_command(
    repo_url: HttpUrl, workdir: str,
    max_repository_bytes: int = DEFAULT_MAX_REPOSITORY_BYTES,
) -> str:
    url = shlex.quote(str(repo_url))
    return (
        "set -eu; "
        "if ! command -v git >/dev/null 2>&1; then "
        "apt-get update -qq && apt-get install -y --no-install-recommends git ca-certificates; fi; "
        f"git clone --depth 1 --filter=blob:none --single-branch -- {url} {REPOSITORY_ROOT}; "
        + repository_size_guard_command(REPOSITORY_ROOT, max_repository_bytes) + "; "
        + project_guard_command(workdir) + "; "
        +
        "python -m venv .venv; "
        ".venv/bin/python -m pip install --disable-pip-version-check -e '.[test]' ruff"
    )


def build_baseline_command(workdir: str) -> str:
    return (
        "set -u; "
        + project_guard_command(workdir) + "; "
        + test_contract_command("CONTRACT_BEFORE") + "; "
        +
        "rm -f /tmp/branchshift-baseline.xml; "
        ".venv/bin/python -m pytest -q --junitxml=/tmp/branchshift-baseline.xml "
        "> /tmp/branchshift-baseline.out 2>&1; test_exit=$?; "
        "cat /tmp/branchshift-baseline.out; "
        "printf '\\n__BRANCHSHIFT_TEST_EXIT=%s\\n' \"$test_exit\"; "
        + junit_metrics_command("/tmp/branchshift-baseline.xml") + "; "
        + runtime_version_command() + "; "
        + test_contract_command("CONTRACT_AFTER") + "; "
        +
        f"printf '__BRANCHSHIFT_COMMIT=%s\\n' \"$(git -C {REPOSITORY_ROOT} rev-parse HEAD)\"; "
        "printf '__BRANCHSHIFT_PYTHON_FILES_BEGIN\\n'; "
        "find . -type f -name '*.py' -not -path './.venv/*' -print | "
        "sed 's#^./##' | LC_ALL=C sort | head -200; "
        "printf '__BRANCHSHIFT_PYTHON_FILES_END\\n'; "
        "printf '__BRANCHSHIFT_MANIFESTS_BEGIN\\n'; "
        "for file in pyproject.toml setup.cfg setup.py requirements.txt; do "
        "test ! -f \"$file\" || printf '%s\\n' \"$file\"; done; "
        "printf '__BRANCHSHIFT_MANIFESTS_END\\n'; "
        "printf '__BRANCHSHIFT_SYMBOL_MATCHES_BEGIN\\n'; "
        "grep -R -n -E 'pydantic|validator|parse_obj|parse_raw|\\.dict\\(' "
        "--include='*.py' --exclude-dir=.venv . 2>/dev/null | head -200 || true; "
        "printf '__BRANCHSHIFT_SYMBOL_MATCHES_END\\n'; "
        "exit 0"
    )


def project_guard_command(workdir: str) -> str:
    path = PurePosixPath(workdir)
    if (
        path.as_posix() != workdir
        or ".." in path.parts
        or not (workdir == REPOSITORY_ROOT or workdir.startswith(f"{REPOSITORY_ROOT}/"))
    ):
        raise ValueError("Project workdir must remain inside the sandbox repository")
    directory = shlex.quote(workdir)
    root = shlex.quote(REPOSITORY_ROOT)
    return (
        f"if [ ! -d {directory} ]; then "
        "printf '%s\\n' 'Selected project path does not exist in the repository' >&2; exit 1; fi; "
        f"cd {directory}; "
        f"case \"$(pwd -P)\" in {root}|{root}/*) ;; *) "
        "printf '%s\\n' 'Selected project path resolves outside the repository' >&2; "
        "exit 1;; esac; "
        "if [ ! -f pyproject.toml ]; then "
        "printf '%s\\n' 'Selected project path has no pyproject.toml' >&2; exit 1; fi"
    )


def _marker_text(output: str, name: str) -> str:
    matches = re.findall(rf"__BRANCHSHIFT_{re.escape(name)}=([^\n]+)", output)
    return matches[-1].strip() if matches else ""


def _section(output: str, name: str) -> list[str]:
    match = re.search(
        rf"__BRANCHSHIFT_{re.escape(name)}_BEGIN\n(.*?)"
        rf"__BRANCHSHIFT_{re.escape(name)}_END",
        output,
        re.DOTALL,
    )
    if not match:
        return []
    return [line.strip()[:500] for line in match.group(1).splitlines() if line.strip()]
