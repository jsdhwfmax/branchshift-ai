import json
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

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
