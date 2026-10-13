import json
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from app.orchestrator.verification import junit_metrics_command, marker_int, marker_text
from app.orchestrator.verification import test_contract_command as contract_command


def test_junit_metrics_are_derived_from_test_cases(tmp_path):
    report = tmp_path / "pytest.xml"
    report.write_text(
        '<testsuites><testsuite><testcase name="pass"/>'
        '<testcase name="failure"><failure/></testcase>'
        '<testcase name="error"><error/></testcase>'
        '<testcase name="skip"><skipped/></testcase></testsuite></testsuites>'
    )
    command = junit_metrics_command(str(report)).replace(
        ".venv/bin/python", shlex.quote(sys.executable), 1
    )
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True, check=True)
    assert marker_int(result.stdout, "TESTS_COLLECTED") == 4
    assert marker_int(result.stdout, "TESTS_PASSED") == 1
    assert marker_int(result.stdout, "TESTS_FAILED") == 2
    assert marker_int(result.stdout, "TESTS_SKIPPED") == 1
    assert json.loads(marker_text(result.stdout, "TEST_OUTCOMES")) == {
        "::pass": "passed", "::failure": "failed", "::error": "failed", "::skip": "skipped",
    }
    assert marker_int(result.stdout, "TEST_OUTCOMES_PRESERVED") == 0


def test_missing_or_duplicate_metrics_fail_closed():
    assert marker_int("1 passed", "TEST_EXIT") == -1
    assert marker_int("__BRANCHSHIFT_TEST_EXIT=0\n" * 2, "TEST_EXIT") == -1
    assert marker_int("ignored __BRANCHSHIFT_TEST_EXIT=0\n", "TEST_EXIT") == -1


def test_contract_preserves_tests_and_config_but_allows_dependency_upgrade(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    case = tests / "test_models.py"
    case.write_text("def test_model(): assert True\n")
    manifest = tmp_path / "pyproject.toml"
    original = ('[project]\ndependencies=["pydantic<2"]\n'
                '[tool.pytest.ini_options]\ntestpaths=["tests"]\n')
    manifest.write_text(original)

    def digest():
        command = contract_command("CONTRACT_BEFORE").replace(
            ".venv/bin/python", shlex.quote(sys.executable), 1
        )
        result = subprocess.run(
            ["sh", "-c", command], cwd=tmp_path, capture_output=True, text=True, check=True
        )
        return marker_text(result.stdout, "CONTRACT_BEFORE")

    baseline = digest()
    assert len(baseline) == 64
    manifest.write_text(original.replace("pydantic<2", "pydantic>=2,<3"))
    assert digest() == baseline
    manifest.write_text(original.replace('testpaths=["tests"]', 'testpaths=["other"]'))
    assert digest() != baseline
    manifest.write_text(original)
    case.write_text("def test_model(): assert False\n")
    assert digest() != baseline


def test_unparseable_contract_reports_one_concise_error_without_claiming_change(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = [pydantic>=2,<3]\n")
    command = contract_command("CONTRACT_BEFORE").replace(
        ".venv/bin/python", shlex.quote(sys.executable), 1
    )
    result = subprocess.run(["sh", "-c", command], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 1
    assert marker_text(result.stdout, "CONTRACT_BEFORE") == ""
    assert "TOMLDecodeError" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
    assert len(result.stdout.splitlines()) == 1


def test_missing_junit_reports_concise_error_without_fake_counts(tmp_path):
    command = junit_metrics_command(str(tmp_path / "missing.xml")).replace(
        ".venv/bin/python", shlex.quote(sys.executable), 1
    )
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True)
    assert result.returncode == 1
    assert "FileNotFoundError" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
    assert marker_int(result.stdout, "TESTS_PASSED") == -1


def test_junit_failure_details_retain_actual_unique_messages_and_test_names(tmp_path):
    report = tmp_path / "failures.xml"
    root = ET.Element("testsuite")
    messages = ["AttributeError: model has no get", "AttributeError: model has no get",
                "Expected original exception type", "Wrong alias behavior " + "x" * 900,
                "Fourth unique failure"]
    for index, message in enumerate(messages):
        case = ET.SubElement(root, "testcase", classname="tests.test_models", name=f"case_{index}")
        ET.SubElement(case, "failure", message=message).text = "Long traceback " * 300
    ET.ElementTree(root).write(report, encoding="unicode")
    command = junit_metrics_command(str(report)).replace(
        ".venv/bin/python", shlex.quote(sys.executable), 1
    )
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True, check=True)
    failures = json.loads(marker_text(result.stdout, "FAILURES"))
    assert len(failures) == 3
    assert failures[0] == {
        "test": "tests.test_models::case_0", "message": "AttributeError: model has no get"
    }
    assert failures[1]["test"].endswith("case_2")
    assert len(failures[2]["message"]) == 600
    assert marker_int(result.stdout, "TESTS_FAILED") == 5


def _run_outcomes(tmp_path, cases, expected=None):
    root = ET.Element("testsuite")
    for classname, name, outcome in cases:
        case = ET.SubElement(root, "testcase", classname=classname, name=name)
        if outcome != "passed":
            ET.SubElement(case, outcome)
    report = tmp_path / "outcomes.xml"
    ET.ElementTree(root).write(report, encoding="unicode")
    command = junit_metrics_command(str(report), expected).replace(
        ".venv/bin/python", shlex.quote(sys.executable), 1
    )
    return subprocess.run(["sh", "-c", command], cwd=tmp_path, capture_output=True, text=True)


@pytest.mark.parametrize(("before", "after", "preserved"), [
    ("passed", "passed", 1),
    ("passed", "skipped", 0),
    ("passed", "failure", 0),
    ("skipped", "skipped", 1),
    ("skipped", "passed", 1),
    ("skipped", "error", 0),
    ("failed", "passed", 0),
])
def test_original_outcome_transitions(tmp_path, before, after, preserved):
    result = _run_outcomes(tmp_path, [("tests.models", "test_item", after)],
                           {"tests.models::test_item": before})
    assert result.returncode == 0
    assert marker_int(result.stdout, "TEST_OUTCOMES_PRESERVED") == preserved
    changed = json.loads(marker_text(result.stdout, "TEST_OUTCOMES_CHANGED"))
    assert len(changed) == (0 if preserved else 1)


@pytest.mark.parametrize("actual", [[], [("other", "test_item", "passed")], [
    ("tests.models", "test_item", "passed"), ("tests.models", "new_test", "passed"),
]])
def test_missing_renamed_or_added_testcase_does_not_preserve_contract(tmp_path, actual):
    result = _run_outcomes(tmp_path, actual, {"tests.models::test_item": "passed"})
    assert result.returncode == 0
    assert marker_int(result.stdout, "TEST_OUTCOMES_PRESERVED") == 0


def test_duplicate_identity_fails_closed_before_counts(tmp_path):
    result = _run_outcomes(tmp_path, [("tests.models", "same", "passed")] * 2)
    assert result.returncode == 1
    assert "Duplicate testcase identity" in marker_text(result.stdout, "METRICS_ERROR")
    assert marker_int(result.stdout, "TESTS_PASSED") == -1
    assert marker_text(result.stdout, "TEST_OUTCOMES") == ""


@pytest.mark.parametrize(("count", "valid"), [(500, True), (501, False)])
def test_outcome_case_limit_is_inclusive(tmp_path, count, valid):
    result = _run_outcomes(tmp_path, [("tests.models", str(i), "passed") for i in range(count)])
    assert result.returncode == (0 if valid else 1)
    assert marker_int(result.stdout, "TESTS_COLLECTED") == (count if valid else -1)


@pytest.mark.parametrize(("extra_byte", "valid"), [(0, True), (1, False)])
def test_outcome_json_byte_limit_is_inclusive(tmp_path, extra_byte, valid):
    overhead = len(json.dumps({"::": "passed"}, separators=(",", ":")).encode())
    name = "x" * (16_000 - overhead + extra_byte)
    result = _run_outcomes(tmp_path, [("", name, "passed")])
    assert result.returncode == (0 if valid else 1)
    if valid:
        assert len(marker_text(result.stdout, "TEST_OUTCOMES").encode()) == 16_000
    else:
        assert marker_text(result.stdout, "TEST_OUTCOMES") == ""


def test_outcome_diagnostics_are_bounded_and_names_are_data(tmp_path):
    name = "$(touch never-created);'\"\\\n" + "x" * 220
    cases = [("tests.models", f"{name}{i}", "skipped") for i in range(6)]
    expected = {f"{cls}::{item}": "passed" for cls, item, _ in cases}
    result = _run_outcomes(tmp_path, cases, expected)
    assert result.returncode == 0
    assert marker_int(result.stdout, "TEST_OUTCOMES_PRESERVED") == 0
    changed = json.loads(marker_text(result.stdout, "TEST_OUTCOMES_CHANGED"))
    assert len(changed) == 3
    assert all(len(item["test"]) == 180 for item in changed)
    assert json.loads(marker_text(result.stdout, "TEST_OUTCOMES")) == {
        identity: "skipped" for identity in expected
    }
    assert not (tmp_path / "never-created").exists()


@pytest.mark.parametrize("expected", [
    {"test::one": "unknown"}, {str(i): "passed" for i in range(501)},
    {"x" * 16_000: "passed"},
])
def test_invalid_expected_outcomes_rejected_before_building_command(expected):
    with pytest.raises(ValueError, match="Expected test outcomes"):
        junit_metrics_command("unused.xml", expected)
