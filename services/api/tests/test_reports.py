import json
from pathlib import Path

import pytest

from app.domain.models import BranchResult, RunEvent, RunStatus, RunSummary
from app.reports import render_markdown_report


def retained_run():
    path = Path(__file__).resolve().parents[3] / "evaluation/evidence/6d863a18d814.json"
    return RunSummary.model_validate_json(path.read_text())


def test_recorded_lint_winner_explanation_preserves_larger_patch_and_history():
    run = retained_run()
    event = RunEvent(
        id=1,
        run_id=run.id,
        type="branch.progress",
        branch_id="compatibility",
        message="Proposal attempt 2/3 started",
        payload={"attempt": 2, "max_attempts": 3},
    )
    before = run.model_dump_json(), event.model_dump_json()
    report = render_markdown_report(run, [event])
    assert "Stored live winner and clean-revalidation evidence satisfy" in report
    assert "Verification scope: the repository's existing test suite" in report
    assert "does not establish behavior equivalence for untested inputs" in report
    assert "installed Pydantic package version" in report
    assert "can still run models through the v1 compatibility API" in report
    assert "do not establish full v2 API adoption" in report
    assert "lint findings is 1 versus 2" in report
    assert "selected patch is larger (71 versus 57 changed lines)" in report
    assert r"nvidia/Nemotron\-3\-Ultra\-550b\-a55b" in report
    assert run.orchestrator_digest in report and run.runtime_config_digest in report
    assert "### minimal" in report and "### compatibility" in report and "### refactor" in report
    assert "Unknown: complete versioned model-usage evidence" in report
    assert "Proposal attempt 2/3 started" in report
    assert "attempt" in report and "max" in report
    assert report == render_markdown_report(run, [event])
    assert before == (run.model_dump_json(), event.model_dump_json())


@pytest.mark.parametrize("missing", ["revalidation", "contract", "patch", "test_exit", "status"])
def test_recorded_winner_alone_cannot_establish_a_verified_live_result(missing):
    run = retained_run()
    if missing == "revalidation":
        run.revalidation = None
    elif missing == "contract":
        run.revalidation.test_contract_preserved = None
    elif missing == "patch":
        run.revalidation.patch = "different retained patch"
    elif missing == "test_exit":
        run.revalidation.test_exit_code = None
    else:
        run.status = RunStatus.FAILED
    report = render_markdown_report(run, [])
    assert "Passing live patch checks are not established" in report
    assert "Stored live winner and clean-revalidation evidence satisfy" not in report


def test_conflicting_selection_is_described_without_replacing_history():
    run = retained_run()
    run.winner_id = "refactor"
    report = render_markdown_report(run, [])
    assert "conflicts with the stored selection; it has not been replaced" in report
    assert "Passing live patch checks are not established" in report
    assert run.winner_id == "refactor"


def test_failed_empty_record_does_not_invent_metrics_usage_or_generated_timestamps():
    run = RunSummary(
        id="partial",
        repo_url="https://github.com/owner/repo",
        mode="live",
        status=RunStatus.FAILED,
        failure_reason="Baseline could not be prepared",
    )
    report = render_markdown_report(run, [])
    assert "No candidate result is recorded" in report
    assert "| Reported input tokens | Unknown (not recorded) |" in report
    assert "| Responses with usage | Unknown (not recorded) |" in report
    assert "| Baseline collected tests | Unknown (not recorded) |" in report
    assert "| Created | Unknown (not recorded) |" in report
    assert "Monetary/credit cost is not established" in report
    assert "No winner is recorded" in report


def test_absent_optional_field_is_not_reported_as_its_model_default():
    run = retained_run()
    winner = next(b for b in run.branches if b.strategy_id == run.winner_id)
    data = winner.model_dump()
    del data["patch_applicable"]
    run.branches = [BranchResult.model_validate(data) if b is winner else b for b in run.branches]
    report = render_markdown_report(run, [])
    assert "| Patch applicable | Unknown (not recorded) |" in report
    assert "Passing live patch checks are not established" in report


def test_untrusted_text_cannot_create_html_markdown_links_tables_or_bidi_controls():
    run = retained_run()
    hostile = (
        "<script>alert(1)</script>\n# Forged | table [click](javascript:alert(1)) ![x](x) ```\u202e"
    )
    run.failure_reason = hostile
    run.branches[0].diagnostics = hostile
    event = RunEvent(
        id=1, run_id=run.id, type="hostile", message=hostile, payload={"data": hostile}
    )
    before = json.dumps(event.model_dump(mode="json"))
    report = render_markdown_report(run, [event])
    assert "<script>" not in report and "\n# Forged" not in report
    assert "[click](javascript:" not in report and "![x](x)" not in report
    assert "```" not in report and "\u202e" not in report
    assert "&lt;script&gt;" in report and r"\|" in report and "u202e" in report
    assert json.dumps(event.model_dump(mode="json")) == before


def test_mock_record_never_claims_live_verification():
    run = retained_run()
    run.mode = "mock"
    report = render_markdown_report(run, [])
    assert "Illustrative sample (mock mode)" in report
    assert "Passing live patch checks are not established" in report


def test_incomplete_usage_and_settled_sdk_calls_are_distinguished_from_billing():
    run = retained_run()
    usage = {
        "model_usage_version": 1,
        "requests": 2,
        "responses_with_usage": 1,
        "input_tokens": 25,
        "output_tokens": 5,
        "sandbox_usage_version": 1,
    }
    for operation in ("sdk_calls", "image_use", "run", "read"):
        for outcome in ("attempted", "completed", "failed", "cancelled"):
            usage[f"sandbox_{operation}_{outcome}"] = 0
    for operation in ("sdk_calls", "run"):
        usage[f"sandbox_{operation}_attempted"] = 1
        usage[f"sandbox_{operation}_failed"] = 1
    run.provider_usage = usage
    report = render_markdown_report(run, [])
    assert "Incomplete: not every attempted model request has response usage" in report
    assert "Sandbox SDK counters are versioned and internally settled" in report
    assert "not internal HTTP requests or billed Sandbox operations" in report
    run.provider_usage["sandbox_sdk_calls_attempted"] = 2
    assert "Sandbox SDK coverage is unknown or unsettled" in render_markdown_report(run, [])


def test_events_from_another_run_are_rejected_instead_of_mixed_into_evidence():
    run = retained_run()
    with pytest.raises(ValueError, match="selected run"):
        render_markdown_report(
            run, [RunEvent(id=1, run_id="other", type="status", message="Other")]
        )


@pytest.mark.parametrize("baseline_passed,baseline_skipped,preserved,skipped,verified", [
    (None, None, None, None, True),  # Historical records retain their original count gate.
    (13, 0, True, 0, True),
    (12, 1, True, 1, True),
    (13, 0, None, 0, False),
    (13, 0, False, 0, False),
    (13, None, True, 0, False),
    (None, 0, True, 0, False),
    (13, 0, True, None, False),
    (13, 1, True, 0, False),
])
def test_report_requires_new_outcome_evidence_when_either_baseline_field_is_recorded(
    baseline_passed, baseline_skipped, preserved, skipped, verified,
):
    run = retained_run()
    run.baseline_tests_passed = baseline_passed
    run.baseline_tests_skipped = baseline_skipped
    for branch in [*run.branches, run.revalidation]:
        branch.test_outcomes_preserved = preserved
        branch.tests_skipped = skipped
        branch.tests_passed = 12 if baseline_passed == 12 else 13
    report = render_markdown_report(run, [])
    assert ("Stored live winner and clean-revalidation evidence satisfy" in report) is verified
    assert ("Passing live patch checks are not established" in report) is not verified


def test_legacy_report_still_requires_the_exact_baseline_collected_count():
    run = retained_run()
    for branch in [*run.branches, run.revalidation]:
        branch.tests_collected = 14
        branch.tests_passed = 14
    report = render_markdown_report(run, [])
    assert "Passing live patch checks are not established" in report
