from app.domain.models import BranchStatus, MigrationStrategy, http_url
from app.orchestrator.branch_runner import BranchRunner, PatchProposal
from app.orchestrator.planner import RepositoryEvidence
from app.providers.base import CommandResult, SandboxState

VALID_PATCH = """diff --git a/src/app/models.py b/src/app/models.py
index 1234567..7654321 100644
--- a/src/app/models.py
+++ b/src/app/models.py
@@ -1 +1 @@
-from pydantic import validator
+from pydantic import field_validator
"""


class FakeModel:
    def __init__(self, patches: list[str]) -> None:
        self.patches = patches
        self.users: list[str] = []

    async def complete_json(self, *, system: str, user: str, schema):
        assert schema is PatchProposal
        assert "unified diff" in system
        self.users.append(user)
        return PatchProposal(patch=self.patches.pop(0), summary="bounded migration")


class FakeSandbox:
    def __init__(self, outputs: list[tuple[str, int]]) -> None:
        self.outputs = outputs
        self.parents: list[SandboxState] = []
        self.commands: list[str] = []

    async def create_base(self, image: str, setup_command: str) -> SandboxState:
        raise AssertionError("not used")

    async def run(self, parent, command, *, timeout_seconds):
        self.parents.append(parent)
        self.commands.append(command)
        output, exit_code = self.outputs.pop(0)
        return CommandResult(
            state=SandboxState(checkpoint_id=f"child-{len(self.commands)}"),
            stdout=output,
            stderr="",
            exit_code=exit_code,
            elapsed_seconds=1.25,
        )

    async def read(self, state: SandboxState, path: str) -> bytes:
        raise AssertionError("not used")


def strategy():
    return MigrationStrategy(
        id="minimal",
        title="Minimal",
        rationale="Smallest migration",
        ordered_steps=["Update validator"],
        source_urls=[http_url("https://docs.pydantic.dev/latest/migration/")],
        target_files=["src/app/models.py"],
    )


def evidence():
    return RepositoryEvidence(
        repo_url="https://github.com/owner/repo",
        dependency_manifests=["pyproject.toml"],
        python_files=["src/app/models.py"],
        symbol_matches=["src/app/models.py:1:validator"],
        baseline_summary="1 passed",
    )


def validation_output(*, passed=1, failed=0, test_exit=0, pip_exit=0, ruff_exit=0):
    return (
        f"{failed} failed, {passed} passed\n"
        f"__BRANCHSHIFT_TEST_EXIT={test_exit}\n"
        f"__BRANCHSHIFT_PIP_EXIT={pip_exit}\n"
        f"__BRANCHSHIFT_RUFF_EXIT={ruff_exit}\n"
    )


async def test_branch_runner_returns_verified_metrics():
    parent = SandboxState(checkpoint_id="baseline")
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(FakeModel([VALID_PATCH]), sandbox).run(
        parent, strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert result.tests_collected == 1
    assert result.tests_passed == 1
    assert result.changed_files == 1
    assert result.changed_lines == 2
    assert sandbox.parents == [parent]
    assert "from pydantic" not in sandbox.commands[0]


async def test_unsafe_first_patch_retries_without_entering_sandbox():
    unsafe = VALID_PATCH.replace("src/app/models.py", "../outside.py")
    model = FakeModel([unsafe, VALID_PATCH])
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert len(sandbox.commands) == 1
    assert "safety validation failed" in model.users[1]


async def test_failed_validation_rebranches_from_same_parent():
    parent = SandboxState(checkpoint_id="baseline")
    sandbox = FakeSandbox(
        [
            (validation_output(passed=0, failed=1, test_exit=1), 0),
            (validation_output(passed=1), 0),
        ]
    )
    result = await BranchRunner(FakeModel([VALID_PATCH, VALID_PATCH]), sandbox).run(
        parent, strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert sandbox.parents == [parent, parent]
    assert result.elapsed_seconds == 2.5


async def test_retry_exhaustion_preserves_failed_evidence():
    failed = validation_output(passed=2, failed=1, test_exit=1, ruff_exit=1)
    sandbox = FakeSandbox([(failed, 0), (failed, 0)])
    result = await BranchRunner(
        FakeModel([VALID_PATCH, VALID_PATCH]), sandbox, max_attempts=2
    ).run(SandboxState(checkpoint_id="baseline"), strategy(), evidence())
    assert result.status is BranchStatus.FAILED
    assert result.tests_collected == 3
    assert result.tests_failed == 1
    assert result.lint_findings == 1
    assert result.patch_applicable is True


async def test_existing_winner_patch_is_revalidated_from_baseline():
    parent = SandboxState(checkpoint_id="baseline")
    sandbox = FakeSandbox([(validation_output(passed=13), 0)])
    runner = BranchRunner(FakeModel([]), sandbox)
    result = await runner.validate_existing_patch(
        parent,
        strategy(),
        VALID_PATCH,
        workdir="/workspace/repo/fixtures/pydantic-v1-app",
    )
    assert result.status is BranchStatus.PASSED
    assert result.tests_passed == 13
    assert sandbox.parents == [parent]


async def test_revalidation_marks_non_applicable_patch():
    sandbox = FakeSandbox([("git apply failed", 1)])
    result = await BranchRunner(FakeModel([]), sandbox).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH
    )
    assert result.status is BranchStatus.FAILED
    assert result.patch_applicable is False
