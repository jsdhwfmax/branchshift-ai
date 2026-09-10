"""Synthetic aggregation tests; none of these records are provider evidence."""
import json
from copy import deepcopy

import pytest

from app.cli.evaluate import aggregate, assess, render


def case(case_id="validators", **overrides):
    return {
        "id": case_id, "minimum_tests": 13,
        "public_repo_url": "https://github.com/jsdhwfmax/branchshift-ai",
        "project_path": "fixtures/pydantic-v1-app", **overrides,
    }


def synthetic_run(run_id="synthetic-1", **overrides):
    branch = {
        "status": "passed", "tests_collected": 13, "tests_passed": 13,
        "tests_failed": 0, "test_exit_code": 0, "pip_exit_code": 0,
        "pip_check_passed": True, "patch_applicable": True,
        "pydantic_major": 2, "test_contract_preserved": True,
    }
    return {
        "id": run_id, "mode": "live", "status": "completed",
        "repo_url": "https://github.com/jsdhwfmax/branchshift-ai",
        "created_at": "2026-09-10T00:00:00+00:00",
        "updated_at": "2026-09-10T00:01:40+00:00",
        "baseline_commit_sha": "a" * 40, "baseline_checkpoint_id": "baseline",
        "baseline_test_contract_digest": "b" * 64, "baseline_tests_collected": 13,
        "model_id": "nvidia/synthetic-test-model", "winner_id": "minimal", "patch": "test diff",
        "revalidated_checkpoint_id": "revalidation",
        "revalidation": dict(branch, checkpoint_id="revalidation", strategy_id="minimal",
                             patch="test diff"),
        "orchestrator_revision": "c" * 40, "orchestrator_digest": "d" * 64,
        "orchestrator_dirty": True, "runtime_config_digest": "e" * 64,
        "branches": [dict(branch, strategy_id=name, checkpoint_id=name)
                     for name in ("minimal", "compatibility", "refactor")],
        "provider_usage": {"requests": 3, "input_tokens": 100, "output_tokens": 50},
        **overrides,
    }


def retained(tmp_path, runs):
    attempts = []
    for index, run in enumerate(runs):
        name = f"{index}.json"
        (tmp_path / name).write_text(json.dumps(run))
        attempts.append({"case_id": "validators", "path": name})
    return attempts


def test_three_repeats_are_one_case_and_dirty_identical_runtime_is_eligible(tmp_path):
    attempts = retained(tmp_path, [synthetic_run(f"synthetic-{n}") for n in range(3)])
    report = aggregate([case()], attempts, tmp_path)
    assert report["qualified_successes"] == 3
    assert report["independent_cases_with_success"] == 1
    assert report["three_consecutive_pass"] is True
    assert report["five_cases_pass"] is False
    assert report["three_successes_per_case"] is False
    assert report["attempts"][0]["orchestrator_dirty"] is True


@pytest.mark.parametrize("change", [
    {"status": "failed"}, {"mode": "mock"}, {"model_id": "nvidia/different-model"},
    {"orchestrator_digest": "f" * 64}, {"runtime_config_digest": "f" * 64},
    {"runtime_config_digest": None}, {"baseline_commit_sha": "f" * 40},
])
def test_latest_failure_or_provenance_change_breaks_three_run_streak(tmp_path, change):
    runs = [synthetic_run(f"synthetic-{n}") for n in range(3)]
    runs[2].update(change)
    report = aggregate([case()], retained(tmp_path, runs), tmp_path)
    assert report["three_consecutive_pass"] is False


@pytest.mark.parametrize("field,value", [
    ("pydantic_major", 1), ("test_contract_preserved", None),
    ("test_exit_code", False), ("tests_passed", 12), ("pip_exit_code", 1),
])
def test_completed_is_not_enough_without_winner_evidence(field, value):
    run = synthetic_run()
    run["branches"][0][field] = value
    assert assess(run, case())["qualified_success"] is False


def test_mock_missing_revalidation_and_wrong_project_do_not_qualify():
    assert not assess(synthetic_run(mode="mock"), case())["qualified_success"]
    assert not assess(synthetic_run(revalidated_checkpoint_id=None), case())["qualified_success"]
    assert not assess(synthetic_run(revalidation=None), case())["qualified_success"]
    assert not assess(synthetic_run(project_path="other"), case())["qualified_success"]
    assert not assess(synthetic_run(), case(public_repo_url=None))["qualified_success"]


def test_revalidation_must_match_patch_and_preserve_runtime_contract():
    run = synthetic_run()
    run["revalidation"]["patch"] = "different patch"
    assert not assess(run, case())["qualified_success"]
    run = synthetic_run()
    run["revalidation"]["test_contract_preserved"] = False
    assert not assess(run, case())["qualified_success"]


def test_duplicate_export_is_rejected_even_when_wrapped_as_api_report(tmp_path):
    run = synthetic_run()
    attempts = retained(tmp_path, [run, {"run": deepcopy(run), "events": []}])
    with pytest.raises(ValueError, match="duplicate exports"):
        aggregate([case()], attempts, tmp_path)


def test_failures_stay_in_denominator_and_unknown_cost_is_not_zero(tmp_path):
    runs = [synthetic_run(), synthetic_run(
        "synthetic-2", status="failed", provider_usage={},
        failure_reason="secret-token-that-must-not-be-in-aggregate: invalid patch",
        updated_at="2026-09-10T00:03:20+00:00",
    )]
    report = aggregate([case()], retained(tmp_path, runs), tmp_path)
    assert report["live_terminal_attempts"] == 2 and report["qualified_successes"] == 1
    assert report["cases"][0]["success_fraction"] == .5
    assert report["median_ledger_seconds"] == 150 and report["p95_ledger_seconds"] == 200
    assert report["observed_usage"]["observed_input_tokens"] == {
        "sum": 100, "records_with_field": 1,
    }
    assert report["total_cost_usd"] is None and report["sandbox_operations"] is None
    assert "secret-token" not in json.dumps(report) + render(report)


def test_empty_manifest_reports_no_evidence(tmp_path):
    report = aggregate([case()], [], tmp_path)
    assert report["qualified_successes"] == report["live_terminal_attempts"] == 0
    assert report["median_ledger_seconds"] is None
    assert report["observed_usage"]["observed_input_tokens"]["sum"] is None
