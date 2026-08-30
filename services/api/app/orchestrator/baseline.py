from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from pydantic import HttpUrl

from app.domain.models import CreateRunRequest
from app.orchestrator.planner import RepositoryEvidence
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
    def __init__(self, sandbox: SandboxProvider, *, timeout_seconds: int = 300) -> None:
        self._sandbox = sandbox
        self._timeout_seconds = timeout_seconds

    async def prepare(
        self,
        image: str,
        repo_url: HttpUrl | str,
    ) -> BaselineOutcome:
        validated_url = CreateRunRequest.model_validate({"repo_url": repo_url}).repo_url
        workdir = repository_workdir(validated_url)
        base = await self._sandbox.create_base(
            image,
            build_setup_command(validated_url, workdir),
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
        test_exit = _marker_int(checked.stdout, "TEST_EXIT")
        passed = _last_int(checked.stdout, r"(\d+) passed")
        failed = _last_int(checked.stdout, r"(\d+) failed")
        if test_exit != 0 or failed or passed == 0:
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
        evidence = RepositoryEvidence(
            repo_url=validated_url,
            dependency_manifests=manifests,
            python_files=python_files,
            symbol_matches=matches,
            baseline_summary=f"{passed + failed} tests collected; {passed} passed; {failed} failed",
        )
        return BaselineOutcome(
            state=checked.state,
            evidence=evidence,
            commit_sha=commit_sha,
            tests_collected=passed + failed,
            tests_passed=passed,
        )


def repository_workdir(repo_url: HttpUrl) -> str:
    normalized = str(repo_url).removesuffix("/").removesuffix(".git")
    if normalized == CONTROLLED_REPOSITORY:
        return f"{REPOSITORY_ROOT}/fixtures/pydantic-v1-app"
    return REPOSITORY_ROOT


def build_setup_command(repo_url: HttpUrl, workdir: str) -> str:
    url = shlex.quote(str(repo_url))
    directory = shlex.quote(workdir)
    return (
        "set -eu; "
        f"git clone --depth 1 --filter=blob:none --single-branch -- {url} {REPOSITORY_ROOT}; "
        f"cd {directory}; "
        "test -f pyproject.toml; "
        "python -m venv .venv; "
        ".venv/bin/python -m pip install --disable-pip-version-check -e '.[test]' ruff"
    )


def build_baseline_command(workdir: str) -> str:
    directory = shlex.quote(workdir)
    return (
        "set -u; "
        f"cd {directory}; "
        ".venv/bin/python -m pytest -q > /tmp/branchshift-baseline.out 2>&1; test_exit=$?; "
        "cat /tmp/branchshift-baseline.out; "
        "printf '\\n__BRANCHSHIFT_TEST_EXIT=%s\\n' \"$test_exit\"; "
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


def _marker_int(output: str, name: str) -> int:
    value = _marker_text(output, name)
    return int(value) if value.isdigit() else -1


def _marker_text(output: str, name: str) -> str:
    matches = re.findall(rf"__BRANCHSHIFT_{re.escape(name)}=([^\n]+)", output)
    return matches[-1].strip() if matches else ""


def _last_int(output: str, pattern: str) -> int:
    matches = re.findall(pattern, output)
    return int(matches[-1]) if matches else 0


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
