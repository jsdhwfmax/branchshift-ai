import pytest

from app.orchestrator.baseline import (
    BaselineError,
    BaselineRunner,
    build_setup_command,
    repository_workdir,
)
from app.providers.base import CommandResult, SandboxState

OUTPUT = """............. [100%]
13 passed in 0.08s
__BRANCHSHIFT_TEST_EXIT=0
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
        raise AssertionError("not used")


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
    ],
)
async def test_invalid_baseline_evidence_fails_closed(output, message):
    with pytest.raises(BaselineError, match=message):
        await BaselineRunner(FakeSandbox(output)).prepare(
            "python:3.13-slim",
            "https://github.com/owner/repo",
        )
