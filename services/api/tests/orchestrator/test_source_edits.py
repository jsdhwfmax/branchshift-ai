import json
import shlex
import subprocess

import pytest
from pydantic import ValidationError

from app.domain.models import BranchStatus, MigrationStrategy, http_url
from app.orchestrator.branch_runner import (
    BranchRunner,
    EditProposal,
    SourceEdit,
    evidence_patch_schema,
    proposal_to_patch,
)
from app.orchestrator.edit_limits import (
    EDIT_BUDGET_DESCRIPTION,
    MAX_EDIT_BYTES,
    MAX_EDITS,
    MAX_NEW_LINES,
    MAX_NEW_LINES_PER_EDIT,
)
from app.orchestrator.patches import UnsafePatch, build_apply_command
from app.orchestrator.planner import RepositoryEvidence
from app.providers.base import CommandResult, ProviderUnavailable, SandboxState

PATH = "src/example.py"


def inputs(source="value = 1\n"):
    plan = MigrationStrategy(
        id="minimal", title="Minimal", rationale="Retain existing behavior",
        ordered_steps=["Migrate existing source"],
        source_urls=[http_url("https://docs.pydantic.dev/latest/migration/")],
        target_files=[PATH],
    )
    evidence = RepositoryEvidence(
        repo_url="https://github.com/example/project", dependency_manifests=[],
        python_files=[PATH], symbol_matches=[], baseline_summary="1 passed",
        file_contents={PATH: source},
    )
    return plan, evidence


def edit(start=1, end=2, lines=None, path=PATH):
    return SourceEdit(path=path, start_line=start, end_line=end,
                      lines=["value = 2"] if lines is None else lines)


def proposal(*edits):
    return EditProposal(edits=list(edits), summary="Small source changes")


@pytest.mark.parametrize("newline, final_newline", [("\n", False), ("\n", True), ("\r\n", True)])
def test_edits_apply_real_git_diff_without_rewriting_unrelated_quote_bytes(
    tmp_path, newline, final_newline,
):
    lines = [
        '"""Preserve "quotes" and the literal text u0022."""',
        "from pydantic import validator", "STYLE = '\"'", "obsolete = True", "",
        "def clean(value):", "    return value",
    ]
    source = newline.join(lines) + (newline if final_newline else "")
    plan, evidence = inputs(source)
    patch = proposal_to_patch(proposal(
        edit(7, 8, ["    return value.strip()"]),
        edit(4, 5, []),
        edit(2, 3, ["from pydantic import field_validator"]),
        edit(6, 6, ["# migration preserves the public function"]),
    ), plan, evidence)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / PATH
    target.parent.mkdir()
    target.write_bytes(source.encode())
    command = build_apply_command(patch).replace(
        "/tmp/branchshift.patch", shlex.quote(str(tmp_path / "candidate.patch"))
    )
    applied = subprocess.run(["sh", "-c", command], cwd=tmp_path, capture_output=True)
    assert applied.returncode == 0, applied.stderr
    expected = (
        lines[0] + newline + "from pydantic import field_validator\n" + lines[2] + newline
        + newline + "# migration preserves the public function\n" + lines[5] + newline
        + "    return value.strip()\n"
    )
    assert target.read_bytes() == expected.encode()
    assert evidence.file_contents[PATH] == source


@pytest.mark.parametrize("source, boundary", [("", 1), ("value = 1", 2), ("value = 1\n", 2)])
def test_empty_file_and_eof_insertions_have_a_real_line_boundary(source, boundary):
    plan, evidence = inputs(source)
    patch = proposal_to_patch(proposal(edit(boundary, boundary, ["other = 2"])), plan, evidence)
    assert "+other = 2" in patch
    if source:
        assert "+value = 1other" not in patch


@pytest.mark.parametrize("ranges", [[(1, 2), (1, 1)], [(1, 3), (2, 2)], [(2, 2), (2, 2)]])
def test_overlapping_or_ambiguous_original_ranges_are_rejected(ranges):
    plan, evidence = inputs("a = 1\nb = 2\n")
    with pytest.raises(UnsafePatch, match="overlap|start boundary"):
        proposal_to_patch(proposal(*(edit(a, b) for a, b in ranges)), plan, evidence)


def test_adjacent_edits_stay_relative_to_baseline_even_when_first_adds_lines():
    plan, evidence = inputs("a = 1\nb = 2\nc = 3\n")
    patch = proposal_to_patch(proposal(
        edit(1, 2, ["a = 10", "extra = 11"]), edit(2, 3, ["b = 20"]),
    ), plan, evidence)
    assert "+extra = 11\n+b = 20\n c = 3" in patch


@pytest.mark.parametrize("start,end", [(2, 1), (1, 3), (3, 3)])
def test_range_is_checked_against_its_own_file_not_global_schema_maximum(start, end):
    plan, evidence = inputs()
    plan.target_files.append("src/long.py")
    evidence.python_files.append("src/long.py")
    evidence.file_contents["src/long.py"] = "# long\n" * 20
    schema = evidence_patch_schema(plan, evidence)
    with pytest.raises(ValidationError, match="range"):
        schema.model_validate(proposal(edit(start, end)).model_dump())


def test_active_schema_is_edits_only_and_rejects_extra_fields_and_non_integer_coordinates():
    plan, evidence = inputs()
    schema = evidence_patch_schema(plan, evidence)
    document = schema.model_json_schema()
    assert set(document["properties"]) == {"edits", "summary"}
    assert document["additionalProperties"] is False
    assert document["$defs"]["EvidenceSourceEdit"]["properties"]["path"]["enum"] == [PATH]
    for invalid in [True, 1.0, "1"]:
        payload = proposal(edit()).model_dump()
        payload["edits"][0]["start_line"] = invalid
        with pytest.raises(ValidationError):
            schema.model_validate(payload)
    with pytest.raises(ValidationError):
        schema.model_validate({"edits": [], "summary": "x", "replacements": []})


def test_shared_capabilities_keep_existing_schema_and_direct_validation_limits():
    assert (MAX_EDITS, MAX_NEW_LINES_PER_EDIT, MAX_NEW_LINES, MAX_EDIT_BYTES) == (
        40, 120, 600, 24_000
    )
    plan, evidence = inputs()
    schema = evidence_patch_schema(plan, evidence).model_json_schema()
    assert schema["properties"]["edits"]["maxItems"] == MAX_EDITS
    assert schema["$defs"]["EvidenceSourceEdit"]["properties"]["lines"]["maxItems"] == (
        MAX_NEW_LINES_PER_EDIT
    )
    assert EDIT_BUDGET_DESCRIPTION in BranchRunner._system_prompt()
    at_limit = edit(lines=["# unchanged purpose"] * 119 + ["value = 2"])
    assert "+value = 2" in proposal_to_patch(proposal(at_limit), plan, evidence)
    outside_limit = SourceEdit.model_construct(
        path=PATH, start_line=1, end_line=2, lines=at_limit.lines + ["# one too many"]
    )
    with pytest.raises(UnsafePatch, match="bounded individual textual lines"):
        proposal_to_patch(proposal(outside_limit), plan, evidence)


@pytest.mark.parametrize(
    "path", ["new.py", "../outside.py", "tests/test_original.py", "pyproject.toml"]
)
def test_direct_edit_path_checks_cannot_be_bypassed_with_a_static_model(path):
    plan, evidence = inputs()
    evidence.dependency_manifests = ["pyproject.toml"]
    with pytest.raises(UnsafePatch, match="retained source|protected|automatically"):
        proposal_to_patch(proposal(edit(path=path)), plan, evidence)


def test_total_edit_budgets_and_text_line_integrity_fail_closed():
    plan, evidence = inputs("# x\n" * 10)
    too_many = EditProposal.model_construct(edits=[edit()] * 41, summary="x")
    with pytest.raises(UnsafePatch, match="count limit"):
        proposal_to_patch(too_many, plan, evidence)
    for candidates in (
        [edit(i, i, ["# new"] * 120) for i in range(1, 7)],
        [edit(1, 2, ["#" + "x" * 4_900] * 5)],
    ):
        with pytest.raises(UnsafePatch, match="size limit"):
            proposal_to_patch(proposal(*candidates), plan, evidence)
    for line in ("first\nsecond", "first\rsecond", "first\x00second"):
        with pytest.raises(UnsafePatch, match="textual lines"):
            proposal_to_patch(proposal(edit(lines=[line])), plan, evidence)
    with pytest.raises(UnsafePatch, match="Empty insertion"):
        proposal_to_patch(proposal(edit(1, 1, [])), plan, evidence)


def test_no_automatic_repair_of_corrupt_quote_tokens():
    plan, evidence = inputs()
    with pytest.raises(UnsafePatch, match="invalid Python"):
        proposal_to_patch(proposal(edit(lines=["u0022u0022u0022bad docstringu0022u0022u0022"])),
                          plan, evidence)


class RecordedModel:
    def __init__(self, proposals):
        self.proposals = proposals
        self.requests = []

    async def complete_json(self, *, system, user, schema):
        self.requests.append({"system": system, "user": user, "schema": schema.model_json_schema()})
        candidate = self.proposals.pop(0)
        if isinstance(candidate, ProviderUnavailable):
            raise candidate
        return schema.model_validate(candidate.model_dump())


class RecordedSandbox:
    def __init__(self):
        self.parents = []

    async def run(self, parent, command, *, timeout_seconds):
        self.parents.append(parent)
        values = {"TEST_EXIT": 0, "PIP_EXIT": 0, "RUFF_EXIT": 0, "INSTALL_EXIT": 0,
                  "TESTS_COLLECTED": 1, "TESTS_PASSED": 1, "TESTS_FAILED": 0, "PYDANTIC_MAJOR": 2}
        return CommandResult(SandboxState("child"), "".join(
            f"__BRANCHSHIFT_{key}={value}\n" for key, value in values.items()
        ), "", 0, 0.1)


async def test_bad_edit_has_local_error_window_and_retry_restarts_from_original():
    source = "# unchanged\n" * 170 + "value = 1\n"
    plan, evidence = inputs(source)
    model = RecordedModel([
        proposal(edit(171, 172, ["def broken(:"])),
        proposal(edit(171, 172, ["value = 2"])),
    ])
    sandbox = RecordedSandbox()
    parent = SandboxState("baseline")
    result = await BranchRunner(model, sandbox, max_attempts=2).run(parent, plan, evidence)
    assert result.status is BranchStatus.PASSED
    assert sandbox.parents == [parent]
    repair = json.loads(model.requests[1]["user"])
    assert repair["original_files"][0]["numbered_source"].endswith("171: value = 1")
    assert "171: def broken(:" in repair["previous_candidate_sources"][0]["numbered_source"]
    assert repair["previous_candidate_edits"][0]["start_line"] == 171
    assert "-value = 1\n+value = 2" in result.patch
    assert "broken" not in result.patch


async def test_read_only_tests_and_complete_encoded_request_stay_under_100kb():
    plan, evidence = inputs()
    for number in range(6):
        path = f"tests/test_{number}.py"
        evidence.python_files.append(path)
        evidence.file_contents[path] = '# assertion context "quote" 汉字\n' * 400
    model = RecordedModel([proposal(edit())])
    await BranchRunner(model, RecordedSandbox()).run(SandboxState("baseline"), plan, evidence)
    request = model.requests[0]
    assert len((json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                + "\n").encode()) <= 100_000
    payload = json.loads(request["user"])
    assert payload["read_only_tests"] and payload["read_only_tests_omitted"]
    for item in payload["read_only_tests"]:
        assert item["source"] == evidence.file_contents[item["path"]]
        assert item["path"] not in payload["editable_source_paths"]
    paths = request["schema"]["$defs"]["EvidenceSourceEdit"]["properties"]["path"]["enum"]
    assert paths == [PATH]


async def test_oversized_required_source_fails_before_a_model_call():
    plan, evidence = inputs("# 汉字\n" * 2_500)
    plan.target_files.append("src/second.py")
    evidence.python_files.append("src/second.py")
    evidence.file_contents["src/second.py"] = evidence.file_contents[PATH]
    model = RecordedModel([])
    with pytest.raises(ProviderUnavailable, match="100000-byte"):
        await BranchRunner(model, RecordedSandbox()).run(SandboxState("baseline"), plan, evidence)
    assert model.requests == []


OUTPUT_LIMIT = "Model response reached the output token limit (finish_reason=length)"


async def test_explicit_output_limit_repairs_with_active_edit_then_executes_once():
    plan, evidence = inputs()
    model = RecordedModel([ProviderUnavailable(OUTPUT_LIMIT), proposal(edit())])
    sandbox = RecordedSandbox()
    parent = SandboxState("baseline")
    result = await BranchRunner(model, sandbox, max_attempts=2).run(parent, plan, evidence)
    assert result.status is BranchStatus.PASSED
    assert len(model.requests) == 2
    assert sandbox.parents == [parent]
    repair = json.loads(model.requests[1]["user"])
    assert OUTPUT_LIMIT in repair["previous_attempt"]
    assert "non-repeating small edits" in repair["previous_attempt"]
    assert EDIT_BUDGET_DESCRIPTION in repair["previous_attempt"]
    assert repair["previous_candidate_diff"] is None
    assert repair["previous_candidate_sources"] == repair["previous_candidate_edits"] == []
    assert set(model.requests[1]["schema"]["properties"]) == {"edits", "summary"}


async def test_schema_repair_reports_the_same_complete_editor_budget():
    plan, evidence = inputs()
    model = RecordedModel([
        ProviderUnavailable("Model returned invalid structured content"), proposal(edit())
    ])
    sandbox = RecordedSandbox()
    result = await BranchRunner(model, sandbox, max_attempts=2).run(
        SandboxState("baseline"), plan, evidence
    )
    assert result.status is BranchStatus.PASSED
    assert len(model.requests) == 2
    assert len(sandbox.parents) == 1
    repair = json.loads(model.requests[1]["user"])
    assert EDIT_BUDGET_DESCRIPTION in repair["previous_attempt"]


async def test_explicit_output_limits_exhaust_existing_attempt_bound_without_execution():
    plan, evidence = inputs()
    model = RecordedModel([ProviderUnavailable(OUTPUT_LIMIT), ProviderUnavailable(OUTPUT_LIMIT)])
    sandbox = RecordedSandbox()
    result = await BranchRunner(model, sandbox, max_attempts=2).run(
        SandboxState("baseline"), plan, evidence
    )
    assert result.status is BranchStatus.FAILED
    assert len(model.requests) == 2
    assert sandbox.parents == []
    assert result.patch is None
    assert "2 attempts" in result.failure_reason
    assert OUTPUT_LIMIT in result.diagnostics


@pytest.mark.parametrize("message", [
    "Nebius request failed",
    "Nebius request failed with HTTP 401",
    "Model returned an invalid response envelope",
])
async def test_other_provider_errors_do_not_repair_or_execute(message):
    plan, evidence = inputs()
    model = RecordedModel([ProviderUnavailable(message)])
    sandbox = RecordedSandbox()
    with pytest.raises(ProviderUnavailable) as caught:
        await BranchRunner(model, sandbox, max_attempts=3).run(
            SandboxState("baseline"), plan, evidence
        )
    assert str(caught.value) == message
    assert len(model.requests) == 1
    assert sandbox.parents == []
