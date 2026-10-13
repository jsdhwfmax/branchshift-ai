import asyncio
import json
import shlex
import subprocess

import pytest
from pydantic import ValidationError

from app.domain.models import BranchStatus, Citation, MigrationStrategy, http_url
from app.orchestrator.branch_runner import (
    BranchRunner,
    FileReplacement,
    PatchProposal,
    evidence_patch_schema,
    proposal_to_patch,
)
from app.orchestrator.patches import UnsafePatch, build_apply_command
from app.orchestrator.planner import RepositoryEvidence
from app.providers.base import CommandResult, ProviderUnavailable, SandboxState

VALID_PATCH = """diff --git a/src/app/models.py b/src/app/models.py
index 1234567..7654321 100644
--- a/src/app/models.py
+++ b/src/app/models.py
@@ -1 +1 @@
-from pydantic import validator
+from pydantic import field_validator
"""


def proposal(path="src/app/models.py", lines=None):
    return PatchProposal(
        replacements=[FileReplacement(
            path=path, lines=lines or ["from pydantic import field_validator"],
        )], summary="bounded migration",
    )


class FakeModel:
    def __init__(self, proposals: list[PatchProposal]) -> None:
        self.proposals = proposals
        self.users: list[str] = []

    async def complete_json(self, *, system: str, user: str, schema):
        assert issubclass(schema, PatchProposal)
        assert "unified diff" in system
        self.users.append(user)
        return self.proposals.pop(0)


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
        file_contents={"src/app/models.py": "from pydantic import validator\n"},
    )


def validation_output(
    *, passed=1, failed=0, test_exit=0, pip_exit=0, ruff_exit=0, major=2, install_exit=0
):
    return (
        f"{failed} failed, {passed} passed\n"
        f"__BRANCHSHIFT_TEST_EXIT={test_exit}\n"
        f"__BRANCHSHIFT_PIP_EXIT={pip_exit}\n"
        f"__BRANCHSHIFT_RUFF_EXIT={ruff_exit}\n"
        f"__BRANCHSHIFT_TESTS_COLLECTED={passed + failed}\n"
        f"__BRANCHSHIFT_TESTS_PASSED={passed}\n"
        f"__BRANCHSHIFT_TESTS_FAILED={failed}\n"
        f"__BRANCHSHIFT_PYDANTIC_MAJOR={major}\n"
        f"__BRANCHSHIFT_INSTALL_EXIT={install_exit}\n"
    )


async def test_branch_runner_returns_verified_metrics():
    parent = SandboxState(checkpoint_id="baseline")
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(FakeModel([proposal()]), sandbox).run(
        parent, strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert result.tests_collected == 1
    assert result.tests_passed == 1
    assert result.changed_files == 1
    assert result.changed_lines == 2
    assert sandbox.parents == [parent]
    assert "from pydantic" not in sandbox.commands[0]
    assert "-e '.[test]' 'pydantic>=2,<3'" in sandbox.commands[0]
    assert result.pydantic_major == 2
    assert result.checkpoint_id == "child-1"


@pytest.mark.parametrize("preserved", [0, 1])
async def test_original_skip_is_allowed_only_with_matching_per_test_outcomes(preserved):
    output = validation_output(passed=1).replace("TESTS_COLLECTED=1", "TESTS_COLLECTED=2")
    output += f"__BRANCHSHIFT_TESTS_SKIPPED=1\n__BRANCHSHIFT_TEST_OUTCOMES_PRESERVED={preserved}\n"
    sandbox = FakeSandbox([(output, 0)])
    result = await BranchRunner(FakeModel([]), sandbox).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH, minimum_tests=2,
        expected_outcomes={"app::one": "passed", "app::known_issue": "skipped"},
    )
    assert result.tests_skipped == 1
    assert result.test_outcomes_preserved is bool(preserved)
    assert result.status is (BranchStatus.PASSED if preserved else BranchStatus.FAILED)
    if not preserved:
        assert "Original test outcomes changed" in result.failure_reason


async def test_unsafe_first_patch_retries_without_entering_sandbox():
    unsafe = proposal("../outside.py")
    model = FakeModel([unsafe, proposal()])
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert len(sandbox.commands) == 1
    assert "safety validation failed" in model.users[1]


@pytest.mark.parametrize("invalid_first", [False, True])
async def test_attempt_callback_precedes_each_proposal_and_stops_after_success(invalid_first):
    observed = []

    class ObservedModel(FakeModel):
        async def complete_json(self, **kwargs):
            observed.append(("model", len(self.users) + 1))
            return await super().complete_json(**kwargs)

    async def on_attempt(attempt, max_attempts):
        observed.append(("progress", attempt, max_attempts))

    proposals = [proposal("../outside.py"), proposal()] if invalid_first else [proposal()]
    sandbox = FakeSandbox([(validation_output(), 0), (validation_output(), 0)])
    runner = BranchRunner(ObservedModel(proposals), sandbox, max_attempts=3)
    result = await runner.run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence(), on_attempt=on_attempt,
    )
    expected = [("progress", 1, 3), ("model", 1)]
    if invalid_first:
        expected += [("progress", 2, 3), ("model", 2)]
    assert observed == expected
    assert result.status is BranchStatus.PASSED
    assert len(sandbox.commands) == 1
    await runner.validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), result.patch,
    )
    assert observed == expected  # Winner revalidation never starts another proposal.


async def test_attempt_callback_keeps_only_started_provider_failure():
    observed = []

    class UnavailableModel:
        async def complete_json(self, **kwargs):
            observed.append("model")
            raise ProviderUnavailable("Service unavailable")

    async def on_attempt(attempt, max_attempts):
        observed.append((attempt, max_attempts))

    with pytest.raises(ProviderUnavailable, match="Service unavailable"):
        await BranchRunner(UnavailableModel(), FakeSandbox([])).run(
            SandboxState(checkpoint_id="baseline"), strategy(), evidence(),
            on_attempt=on_attempt,
        )
    assert observed == [(1, 3), "model"]


async def test_attempt_callback_does_not_emit_after_inflight_cancellation():
    observed = []
    started = asyncio.Event()

    class BlockedModel:
        async def complete_json(self, **kwargs):
            observed.append("model")
            started.set()
            await asyncio.Event().wait()

    async def on_attempt(attempt, max_attempts):
        observed.append((attempt, max_attempts))

    task = asyncio.create_task(BranchRunner(BlockedModel(), FakeSandbox([])).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence(), on_attempt=on_attempt,
    ))
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert observed == [(1, 3), "model"]


@pytest.mark.parametrize("error", [UnsafePatch("Observer failed"), asyncio.CancelledError()])
async def test_attempt_observer_failure_propagates_without_model_request_or_retry(error):
    observed = []
    model = FakeModel([proposal()])

    async def on_attempt(attempt, max_attempts):
        observed.append((attempt, max_attempts))
        raise error

    with pytest.raises(type(error)):
        await BranchRunner(model, FakeSandbox([])).run(
            SandboxState(checkpoint_id="baseline"), strategy(), evidence(),
            on_attempt=on_attempt,
        )
    assert observed == [(1, 3)]
    assert model.users == []


async def test_failed_validation_rebranches_from_same_parent():
    parent = SandboxState(checkpoint_id="baseline")
    sandbox = FakeSandbox(
        [
            (validation_output(passed=0, failed=1, test_exit=1), 0),
            (validation_output(passed=1), 0),
        ]
    )
    result = await BranchRunner(FakeModel([proposal(), proposal()]), sandbox).run(
        parent, strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert sandbox.parents == [parent, parent]
    assert result.elapsed_seconds == 2.5


async def test_retry_exhaustion_preserves_failed_evidence():
    failed = validation_output(passed=2, failed=1, test_exit=1, ruff_exit=1)
    sandbox = FakeSandbox([(failed, 0), (failed, 0)])
    result = await BranchRunner(
        FakeModel([proposal(), proposal()]), sandbox, max_attempts=2
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


@pytest.mark.parametrize(
    "output",
    [
        "13 passed in 0.1s\n",  # Repository stdout alone is not verification.
        validation_output(major=1),
        validation_output(install_exit=1),
        validation_output().replace("__BRANCHSHIFT_PIP_EXIT=0\n", ""),
        validation_output() + "__BRANCHSHIFT_TEST_EXIT=0\n",
    ],
)
async def test_incomplete_or_non_v2_validation_never_passes(output):
    sandbox = FakeSandbox([(output, 0)])
    result = await BranchRunner(FakeModel([]), sandbox).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH
    )
    assert result.status is BranchStatus.FAILED


async def test_dropped_baseline_tests_fail_validation():
    sandbox = FakeSandbox([(validation_output(passed=1), 0)])
    result = await BranchRunner(FakeModel([]), sandbox).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH, minimum_tests=13
    )
    assert result.status is BranchStatus.FAILED


async def test_repair_receives_actual_bounded_diagnostic():
    model = FakeModel([proposal(), proposal()])
    sandbox = FakeSandbox([
        ("ImportError: cannot import field_validator\n" + validation_output(test_exit=2), 0),
        (validation_output(), 0),
    ])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert "ImportError: cannot import field_validator" in model.users[1]


@pytest.mark.parametrize("after", ["a" * 64, "b" * 64, ""])
async def test_immutable_test_contract_is_required_when_baseline_provides_it(after):
    digest = "a" * 64
    output = validation_output() + (
        f"__BRANCHSHIFT_CONTRACT_BEFORE={digest}\n"
        f"__BRANCHSHIFT_CONTRACT_AFTER={after}\n"
    )
    result = await BranchRunner(FakeModel([]), FakeSandbox([(output, 0)])).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH,
        test_contract_digest=digest,
    )
    assert result.test_contract_preserved is ((after == digest) if after else None)
    assert (result.status is BranchStatus.PASSED) is (after == digest)
    if not after:
        assert "could not be verified" in result.failure_reason
        assert "changed" not in result.failure_reason


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("original_newline", [False, True])
def test_line_replacements_derive_real_applicable_diff(tmp_path, nested, original_newline):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    project = tmp_path / "fixtures" / "target" if nested else tmp_path
    target = project / "src" / "app" / "models.py"
    target.parent.mkdir(parents=True)
    original = 'from pydantic import validator\n\ndef clean(value):\n    return value.strip()'
    if original_newline:
        original += "\n"
    target.write_text(original)
    retained = evidence()
    retained.file_contents["src/app/models.py"] = original
    lines = [
        "from pydantic import field_validator", "", "def clean(value):",
        '    return value.strip(" ")',
    ]
    patch = proposal_to_patch(proposal(lines=lines), strategy(), retained)
    command = build_apply_command(patch).replace(
        "/tmp/branchshift.patch", shlex.quote(str(tmp_path / "candidate.patch"))
    )
    applied = subprocess.run(["sh", "-c", command], cwd=project, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    assert target.read_text() == "\n".join(lines) + "\n"
    assert patch.startswith("diff --git a/src/app/models.py b/src/app/models.py\n")


@pytest.mark.parametrize(
    "candidate, message",
    [
        (proposal("new.py"), "retained source"),
        (proposal("tests/test_models.py"), "protected test"),
        (proposal(lines=["from pydantic import validator"]), "unchanged"),
        (proposal(lines=["first\nsecond"]), "one textual line"),
        (proposal(lines=["x" * 5_000] * 6), "bounded source size"),
    ],
)
def test_unsafe_replacements_fail_before_sandbox(candidate, message):
    with pytest.raises(UnsafePatch, match=message):
        proposal_to_patch(candidate, strategy(), evidence())


def test_duplicate_replacement_file_is_rejected():
    candidate = proposal()
    candidate.replacements *= 2
    with pytest.raises(UnsafePatch, match="duplicate"):
        proposal_to_patch(candidate, strategy(), evidence())


async def test_exhausted_unsafe_proposals_store_actionable_diagnostics():
    sandbox = FakeSandbox([])
    result = await BranchRunner(
        FakeModel([proposal("new.py"), proposal("new.py")]), sandbox, max_attempts=2
    ).run(SandboxState(checkpoint_id="baseline"), strategy(), evidence())
    assert result.status is BranchStatus.FAILED
    assert result.patch is None
    assert "2 attempts" in result.failure_reason
    assert "retained source" in result.diagnostics
    assert sandbox.commands == []


def test_model_schema_requests_line_arrays_instead_of_diff_syntax():
    schema = PatchProposal.model_json_schema()
    assert "replacements" in schema["required"]
    assert "patch" not in schema["properties"]
    replacement = schema["$defs"]["FileReplacement"]
    assert set(replacement["required"]) == {"path", "lines"}
    assert replacement["properties"]["lines"]["type"] == "array"


async def test_model_manifest_rewrite_is_rejected_and_pin_is_updated_automatically():
    retained = evidence()
    retained.file_contents["pyproject.toml"] = '[project]\ndependencies = ["pydantic<2"]\n'
    plan = strategy()
    plan.target_files.append("pyproject.toml")
    model = FakeModel([
        proposal("pyproject.toml", ["[project]", "dependencies = [pydantic>=2,<3]"]),
        proposal(),
    ])
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), plan, retained
    )
    assert result.status is BranchStatus.PASSED
    assert len(sandbox.commands) == 1
    assert "manifests are updated automatically" in model.users[1]
    assert '+dependencies = ["pydantic>=2,<3"]' in result.patch
    assert result.changed_files == 2
    assert result.changed_lines == 4
    payload = json.loads(model.users[0])
    assert payload["editable_source_paths"] == ["src/app/models.py"]
    assert [item["path"] for item in payload["original_files"]] == ["src/app/models.py"]
    assert payload["automatic_dependency_changes"]["changed_manifests"] == ["pyproject.toml"]


async def test_unavailable_contract_does_not_claim_tampering_after_install_failure():
    result = await BranchRunner(
        FakeModel([]), FakeSandbox([(validation_output(install_exit=2), 0)])
    ).validate_existing_patch(
        SandboxState(checkpoint_id="baseline"), strategy(), VALID_PATCH,
        test_contract_digest="a" * 64,
    )
    assert result.test_contract_preserved is None
    assert result.status is BranchStatus.FAILED
    assert result.failure_reason.startswith("Dependency installation failed")


async def test_junit_error_survives_long_output_and_reaches_repair_prompt():
    message = "AttributeError: 'Record' object has no attribute 'get'"
    failures = json.dumps([{"test": "tests.test_models::test_valid_record", "message": message}])
    noisy_output = (
        "Package installation chatter\n" * 500
        + validation_output(passed=1, failed=12, test_exit=1)
        + f"__BRANCHSHIFT_FAILURES={failures}\n"
        + "Warnings summary\n" * 500
    )
    model = FakeModel([proposal(), proposal()])
    sandbox = FakeSandbox([(noisy_output, 0), (validation_output(), 0)])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    repair = json.loads(model.users[1])["previous_attempt"]
    assert message in repair[:1_000]
    assert "test_valid_record" in repair[:1_000]
    assert len(repair) <= 4_000
    assert "--tb=short --disable-warnings" in sandbox.commands[0]
    context = json.loads(model.users[1])
    assert "+from pydantic import field_validator" in context["previous_candidate_diff"]
    assert context["original_files"][0]["lines"] == ["from pydantic import validator"]


def test_previous_candidate_context_is_bounded_and_labeled_separately():
    payload = json.loads(BranchRunner._user_prompt(
        strategy(), evidence(), "A bounded failure", previous_candidate_diff="x" * 13_000
    ))
    assert len(payload["previous_candidate_diff"]) == 12_000
    assert payload["previous_candidate_diff_truncated"] is True
    assert payload["original_files"][0]["lines"] == ["from pydantic import validator"]


async def test_unsafe_repair_does_not_reuse_an_unrelated_previous_candidate_diff():
    model = FakeModel([proposal(), proposal("invented.py"), proposal()])
    sandbox = FakeSandbox([
        (validation_output(passed=0, failed=1, test_exit=1), 0), (validation_output(), 0)
    ])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert json.loads(model.users[1])["previous_candidate_diff"] is not None
    assert json.loads(model.users[2])["previous_candidate_diff"] is None
    assert "unknown" not in json.loads(model.users[0])["previous_attempt"]


async def test_editor_receives_actual_bounded_retained_guidance():
    model = FakeModel([proposal()])
    source = Citation(
        title="Retained official migration guidance",
        url=http_url("https://docs.pydantic.dev/latest/migration/"),
        evidence="Retained documentation excerpt: " + "x" * 3_200,
    )
    await BranchRunner(model, FakeSandbox([(validation_output(), 0)])).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence(), citations=[source]
    )
    guidance = json.loads(model.users[0])["official_guidance"]
    assert guidance == [{
        "title": source.title, "url": str(source.url), "evidence": source.evidence[:3_000]
    }]
    empty = json.loads(BranchRunner._user_prompt(strategy(), evidence(), ""))
    assert empty["official_guidance"] == []


def manifest_evidence():
    retained = evidence()
    retained.file_contents["pyproject.toml"] = (
        '# metadata must survive\n[project]\nname = "example"\nversion = "0.1.0"\n'
        'dependencies = ["pydantic[email]>=1.10,<2", "httpx>=0.28"] # keep\n'
    )
    plan = strategy()
    plan.target_files.append("pyproject.toml")
    return plan, retained


def test_editor_schema_enum_contains_only_declared_retained_non_test_sources():
    plan, retained = manifest_evidence()
    retained.python_files.extend(["src/other.py", "tests/test_model.py"])
    retained.file_contents.update({"src/other.py": "pass\n", "tests/test_model.py": "pass\n"})
    plan.target_files.append("tests/test_model.py")
    schema = evidence_patch_schema(plan, retained)
    encoded = schema.model_json_schema()
    paths = encoded["$defs"]["EvidenceFileReplacement"]["properties"]["path"]
    assert paths["enum"] == ["src/app/models.py"]
    assert encoded["properties"]["replacements"]["minItems"] == 0
    schema.model_validate(proposal().model_dump())
    for path in ["pyproject.toml", "tests/test_model.py", "src/other.py", "invented.py"]:
        with pytest.raises(ValidationError):
            schema.model_validate(proposal(path).model_dump())


def test_empty_source_proposal_requires_a_real_automatic_manifest_change():
    plan, retained = manifest_evidence()
    empty = PatchProposal(replacements=[], summary="No source changes necessary")
    schema = evidence_patch_schema(plan, retained)
    schema.model_validate(empty.model_dump())
    patch = proposal_to_patch(empty, plan, retained)
    assert "diff --git a/pyproject.toml b/pyproject.toml" in patch
    assert "+dependencies" in patch
    with pytest.raises(UnsafePatch, match="unchanged"):
        proposal_to_patch(empty, strategy(), evidence())
    with pytest.raises(ValidationError):
        evidence_patch_schema(strategy(), evidence()).model_validate(empty.model_dump())


def test_manifest_only_strategy_schema_allows_only_an_empty_source_array():
    plan, retained = manifest_evidence()
    plan.target_files = ["pyproject.toml"]
    schema = evidence_patch_schema(plan, retained)
    constraints = schema.model_json_schema()["properties"]["replacements"]
    assert constraints["maxItems"] == constraints["minItems"] == 0
    schema.model_validate({"replacements": [], "summary": "Dependency update only"})
    with pytest.raises(ValidationError):
        schema.model_validate(proposal("pyproject.toml").model_dump())


def test_model_cannot_rewrite_manifest_even_when_bypassing_dynamic_schema():
    plan, retained = manifest_evidence()
    with pytest.raises(UnsafePatch, match="manifests are updated automatically"):
        proposal_to_patch(proposal("pyproject.toml", ["broken TOML"]), plan, retained)


@pytest.mark.parametrize("nested", [False, True])
def test_deterministic_manifest_and_generated_source_apply_as_one_real_patch(tmp_path, nested):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    project = tmp_path / "fixtures" / "target" if nested else tmp_path
    target = project / "src" / "app" / "models.py"
    target.parent.mkdir(parents=True)
    plan, retained = manifest_evidence()
    for name, content in retained.file_contents.items():
        (project / name).write_text(content)
    patch = proposal_to_patch(proposal(), plan, retained)
    command = build_apply_command(patch).replace(
        "/tmp/branchshift.patch", shlex.quote(str(tmp_path / "candidate.patch"))
    )
    applied = subprocess.run(["sh", "-c", command], cwd=project, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    assert target.read_text() == "from pydantic import field_validator\n"
    assert (project / "pyproject.toml").read_text() == retained.file_contents[
        "pyproject.toml"
    ].replace("pydantic[email]>=1.10,<2", "pydantic[email]>=2,<3")


async def test_invalid_python_repair_receives_actual_rejected_source_with_line_numbers():
    broken = proposal(lines=["from pydantic import field_validator", "", "def clean(:", "    pass"])
    model = FakeModel([broken, proposal()])
    sandbox = FakeSandbox([(validation_output(), 0)])
    result = await BranchRunner(model, sandbox).run(
        SandboxState(checkpoint_id="baseline"), strategy(), evidence()
    )
    assert result.status is BranchStatus.PASSED
    assert len(sandbox.commands) == 1
    repair = json.loads(model.users[1])
    assert "invalid Python" in repair["previous_attempt"]
    assert repair["previous_candidate_diff"] is None
    assert repair["previous_candidate_sources"] == [{
        "path": "src/app/models.py",
        "numbered_source": (
            "1: from pydantic import field_validator\n2: \n3: def clean(:\n4:     pass"
        ),
        "truncated": False,
    }]
    assert repair["original_files"][0]["lines"] == ["from pydantic import validator"]


def test_rejected_source_context_is_bounded():
    oversized = proposal(lines=["#" + "x" * 4_999] * 20)
    payload = json.loads(BranchRunner._user_prompt(
        strategy(), evidence(), "Source rejected", previous_proposal=oversized
    ))
    context = payload["previous_candidate_sources"]
    assert len(context[0]["numbered_source"]) == 6_000
    assert context[0]["truncated"] is True
