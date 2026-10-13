"""Offline guard/receipt tests. No checkout, package install, candidate, or model execution."""

import json
import tarfile
from types import SimpleNamespace

import pytest
import run_manual as manual


def request():
    return manual.read_json(manual.HERE / "candidate-input/request.json")


def stdout(**overrides):
    values = {
        "TEST_EXIT": 0, "PIP_EXIT": 0, "INSTALL_EXIT": 0, "TESTS_COLLECTED": 15,
        "TESTS_PASSED": 14, "TESTS_FAILED": 0, "TESTS_SKIPPED": 1,
        "TEST_OUTCOMES_PRESERVED": 1, "PYDANTIC_MAJOR": 2,
    }
    values.update(overrides)
    return "".join(f"__BRANCHSHIFT_{key}={value}\n" for key, value in values.items())


def check():
    return {key: True for key in (
        "observed_exact_tree", "test_contract_preserved", "full_runtime_preserved"
    )}


def test_actual_manual_input_matches_original_protocol_and_all_hashes():
    raw, metadata = manual.validate_inputs(
        manual.HERE / "candidate-input", manual.HERE / "frozen", None
    )
    assert metadata["model_calls"] == 0
    assert metadata["manual_role"] == "candidate"
    assert raw["patch_sha256"] == (
        "c1d9c8d185177a3d78a55a2fd20c213bbf3c424471e2cdf90930d6900a8582be"
    )


@pytest.mark.parametrize("field,value", [
    ("authoring_method", "autonomous"), ("model_calls", 1), ("model_calls", False),
    ("manual_iteration", 0), ("manual_iteration", 5), ("manual_iteration", True),
])
def test_manual_authorship_and_iteration_bounds_are_explicit(field, value):
    value_request = {**request(), field: value}
    with pytest.raises(ValueError):
        manual.manual_metadata(value_request, None)


@pytest.mark.parametrize("overrides", [
    {"TEST_EXIT": 1}, {"PIP_EXIT": 1}, {"INSTALL_EXIT": 1}, {"TESTS_COLLECTED": 14},
    {"TESTS_PASSED": 13}, {"TESTS_FAILED": 1}, {"TESTS_SKIPPED": 0},
    {"TEST_OUTCOMES_PRESERVED": 0}, {"PYDANTIC_MAJOR": 1},
])
def test_shell_completion_never_substitutes_for_observed_command_checks(overrides):
    assert manual.original_command_gate(stdout(**overrides))["passed"] is False


def test_missing_or_duplicate_markers_fail_closed_without_promoting_lint():
    assert manual.original_command_gate(stdout())["passed"] is True
    assert manual.original_command_gate(stdout() + "__BRANCHSHIFT_RUFF_EXIT=1\n")["passed"]
    assert manual.original_command_gate("")["passed"] is False
    assert manual.original_command_gate(stdout() + "__BRANCHSHIFT_TEST_EXIT=0\n")["passed"] is False


def qualified_report():
    raw = request()
    return {
        **manual.manual_metadata(raw, None), "status": "candidate_validation_complete",
        "execution_environment": "github-hosted-runner",
        "upstream_commit": manual.protocol.UPSTREAM_SHA,
        "candidate_native_migration_qualified": True,
        "manual_original_command_gate": manual.original_command_gate(stdout()),
        **{key: raw[key] for key in ("patch_sha256", "command_sha256",
                                   "baseline_context_sha256", "candidate_constraints_sha256")},
    }


def test_repeat_requires_same_qualified_patch_and_complete_application_checks(tmp_path):
    repeat = {**request(), "phase": "revalidation"}
    with pytest.raises(ValueError, match="requires"):
        manual.manual_metadata(repeat, None)
    manual.protocol.save(tmp_path / "summary.json", qualified_report())
    manual.protocol.save(tmp_path / "validation/application-check.json", check())
    assert manual.manual_metadata(repeat, tmp_path)["manual_role"] == "clean_repeat"
    for changed in ({"patch_sha256": "0" * 64}, {"command_sha256": "0" * 64},
                    {"manual_iteration": 2}):
        with pytest.raises(ValueError, match="same qualified"):
            manual.manual_metadata({**repeat, **changed}, tmp_path)
    manual.protocol.save(tmp_path / "validation/application-check.json", {
        **check(), "full_runtime_preserved": False,
    })
    with pytest.raises(ValueError, match="checks did not qualify"):
        manual.manual_metadata(repeat, tmp_path)


@pytest.mark.parametrize("protocol_pass,has_check,command_pass", [
    (True, True, True), (False, True, True), (True, False, True), (True, True, False),
])
def test_final_archive_always_contains_summary_and_application_status(
    tmp_path, monkeypatch, protocol_pass, has_check, command_pass,
):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    output = tmp_path / "evidence"
    (output / "validation").mkdir(parents=True)
    (output / "validation/stdout.txt").write_text(stdout(TEST_EXIT=0 if command_pass else 1))
    if has_check:
        manual.protocol.save(output / "validation/application-check.json", check())
    runner = SimpleNamespace(output=output, report={
        "candidate_native_migration_qualified": protocol_pass,
    })
    archive = manual.finish(runner)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["candidate_native_migration_qualified"] is (
        protocol_pass and has_check and command_pass
    )
    with tarfile.open(archive) as stream:
        assert {"summary.json", "validation/application-check.json"} <= set(stream.getnames())
    assert archive.stat().st_size <= 5 * 1024 * 1024


def test_execution_guard_refuses_developer_host(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(SystemExit, match="Refusing execution"):
        manual.protocol.guard_runner()
