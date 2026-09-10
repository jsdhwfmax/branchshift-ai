import subprocess

import pytest

from app.orchestrator.baseline import (
    BaselineError,
    BaselineRunner,
    build_setup_command,
    project_guard_command,
    repository_workdir,
)
from app.providers.base import CommandResult, SandboxState

OUTPUT = """............. [100%]
13 passed in 0.08s
__BRANCHSHIFT_TEST_EXIT=0
__BRANCHSHIFT_TESTS_COLLECTED=13
__BRANCHSHIFT_TESTS_PASSED=13
__BRANCHSHIFT_TESTS_FAILED=0
__BRANCHSHIFT_PYDANTIC_MAJOR=1
__BRANCHSHIFT_CONTRACT_BEFORE=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__BRANCHSHIFT_CONTRACT_AFTER=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
__BRANCHSHIFT_COMMIT=0123456789abcdef0123456789abcdef01234567
__BRANCHSHIFT_PYTHON_FILES_BEGIN
src/sample_app/models.py
tests/test_models.py
__BRANCHSHIFT_PYTHON_FILES_END
__BRANCHSHIFT_MANIFESTS_BEGIN
pyproject.toml
__BRANCHSHIFT_MANIFESTS_END
__BRANCHSHIFT_SYMBOL_MATCHES_BEGIN
src/sample_app/models.py:7:from pydantic import validator
__BRANCHSHIFT_SYMBOL_MATCHES_END
"""


class FakeSandbox:
    def __init__(self, output: str = OUTPUT, exit_code: int = 0) -> None:
        self.output = output
        self.exit_code = exit_code
        self.setup_command = ""
        self.parent: SandboxState | None = None
        self.read_paths: list[str] = []

    async def create_base(self, image: str, setup_command: str) -> SandboxState:
        assert image == "python:3.13-slim"
        self.setup_command = setup_command
        return SandboxState(checkpoint_id="installed")

    async def run(self, parent, command, *, timeout_seconds):
        self.parent = parent
        assert timeout_seconds == 300
        return CommandResult(
            state=SandboxState(checkpoint_id="baseline"),
            stdout=self.output,
            stderr="",
            exit_code=self.exit_code,
            elapsed_seconds=2.0,
        )

    async def read(self, state: SandboxState, path: str) -> bytes:
        assert state.checkpoint_id == "baseline"
        self.read_paths.append(path)
        if path.endswith("pyproject.toml"):
            return b'[project]\ndependencies = ["pydantic>=1.10,<2"]\n'
        return b"from pydantic import validator\n"


async def test_controlled_fixture_prepares_passing_checkpoint():
    sandbox = FakeSandbox()
    outcome = await BaselineRunner(sandbox).prepare(
        "python:3.13-slim",
        "https://github.com/jsdhwfmax/branchshift-ai",
    )
    assert outcome.state.checkpoint_id == "baseline"
    assert outcome.tests_collected == 13
    assert outcome.tests_passed == 13
    assert outcome.evidence.python_files == [
        "src/sample_app/models.py",
        "tests/test_models.py",
    ]
    assert "fixtures/pydantic-v1-app" in sandbox.setup_command
    assert sandbox.parent == SandboxState(checkpoint_id="installed")
    assert outcome.evidence.baseline_tests_collected == 13
    assert "pydantic>=1.10,<2" in outcome.evidence.file_contents["pyproject.toml"]


async def test_configured_repository_limit_reaches_remote_setup_guard():
    sandbox = FakeSandbox()
    await BaselineRunner(sandbox, max_repository_bytes=123_456).prepare(
        "python:3.13-slim", "https://github.com/owner/repo",
    )
    assert "/workspace/repo 123456; " in sandbox.setup_command
    assert sandbox.setup_command.index("ls-files") < sandbox.setup_command.index("-m venv")


def test_arbitrary_repository_uses_repository_root():
    from app.domain.models import http_url

    url = http_url("https://github.com/owner/repo")
    assert repository_workdir(url) == "/workspace/repo"
    command = build_setup_command(url, repository_workdir(url))
    assert "--depth 1" in command
    assert "https://github.com/owner/repo" in command


@pytest.mark.parametrize(
    "output, message",
    [
        (
            OUTPUT.replace("13 passed", "1 failed, 12 passed").replace(
                "TEST_EXIT=0", "TEST_EXIT=1"
            ),
            "must pass",
        ),
        (OUTPUT.replace("0123456789abcdef0123456789abcdef01234567", "not-a-sha"), "commit SHA"),
        (OUTPUT.replace("pyproject.toml\n", "", 1), "supported manifest"),
        (OUTPUT.replace("__BRANCHSHIFT_TESTS_COLLECTED=13\n", ""), "must pass"),
        (OUTPUT.replace("PYDANTIC_MAJOR=1", "PYDANTIC_MAJOR=2"), "Pydantic v1"),
    ],
)
async def test_invalid_baseline_evidence_fails_closed(output, message):
    with pytest.raises(BaselineError, match=message):
        await BaselineRunner(FakeSandbox(output)).prepare(
            "python:3.13-slim",
            "https://github.com/owner/repo",
        )


async def test_oversized_manifest_fails_before_planning():
    class OversizedManifestSandbox(FakeSandbox):
        async def read(self, state, path):
            return b"x" * 25_001

    with pytest.raises(BaselineError, match="source evidence limit"):
        await BaselineRunner(OversizedManifestSandbox()).prepare(
            "python:3.13-slim", "https://github.com/owner/repo"
        )


async def test_explicit_monorepo_project_path_controls_setup_and_evidence_reads():
    sandbox = FakeSandbox()
    await BaselineRunner(sandbox).prepare(
        "python:3.13-slim", "https://github.com/jsdhwfmax/branchshift-ai",
        project_path="fixtures/config-case",
    )
    assert "cd /workspace/repo/fixtures/config-case" in sandbox.setup_command
    assert sandbox.read_paths
    assert all(
        path.startswith("/workspace/repo/fixtures/config-case/") for path in sandbox.read_paths
    )


def test_optional_project_path_overrides_controlled_default_and_rejects_traversal():
    from app.domain.models import http_url

    url = http_url("https://github.com/jsdhwfmax/branchshift-ai")
    assert repository_workdir(url) == "/workspace/repo/fixtures/pydantic-v1-app"
    assert repository_workdir(url, "packages/models") == "/workspace/repo/packages/models"
    with pytest.raises(ValueError, match="repository-relative"):
        repository_workdir(url, "../outside")


@pytest.mark.parametrize("kind", ["missing", "no-manifest", "symlink-outside", "valid"])
def test_project_guard_reports_actual_path_problem_without_running_repository_code(
    tmp_path, monkeypatch, kind
):
    from app.orchestrator import baseline

    root = tmp_path.resolve() / "repo"
    root.mkdir()
    monkeypatch.setattr(baseline, "REPOSITORY_ROOT", str(root))
    project = root / "target"
    if kind == "symlink-outside":
        outside = tmp_path.resolve() / "outside"
        outside.mkdir()
        (outside / "pyproject.toml").write_text("[project]\n")
        project.symlink_to(outside, target_is_directory=True)
    elif kind != "missing":
        project.mkdir()
        if kind == "valid":
            (project / "pyproject.toml").write_text("[project]\n")
    result = subprocess.run(
        ["sh", "-c", project_guard_command(str(project))], capture_output=True, text=True
    )
    if kind == "valid":
        assert result.returncode == 0
    else:
        assert result.returncode == 1
        reason = {
            "missing": "does not exist",
            "no-manifest": "has no pyproject.toml",
            "symlink-outside": "resolves outside",
        }[kind]
        assert reason in result.stderr
