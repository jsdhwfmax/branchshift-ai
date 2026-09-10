"""Synthetic runner checks: all records live only in pytest's temporary directory."""
import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.config import Settings

COMMIT = "a" * 40
SOURCE = "b" * 64
CONFIG = "c" * 64
MODEL = "nvidia/synthetic-runner-test"


@pytest.fixture
def runner_case(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[4] / "evaluation" / "run_evaluation.py"
    spec = importlib.util.spec_from_file_location("synthetic_series_runner", path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "settings", Settings(
        mode="live", nemotron_model=MODEL, nebius_api_key="synthetic-key",
        nebius_project_id="synthetic-project", tavily_api_key="synthetic-search-key",
    ))
    source = {
        "orchestrator_revision": "d" * 40, "orchestrator_digest": SOURCE,
        "orchestrator_dirty": True,
    }
    source_lookup = Mock(side_effect=lambda: dict(source))
    remote_lookup = Mock(return_value=f"{COMMIT}\tHEAD\n")
    monkeypatch.setattr(runner, "source_provenance", source_lookup)
    monkeypatch.setattr(runner, "runtime_config_digest", lambda settings: CONFIG)
    monkeypatch.setattr(runner.subprocess, "check_output", remote_lookup)
    cases = [{
        "id": f"case-{index}", "project_path": f"synthetic/case-{index}",
        "public_repo_url": "https://github.com/example/synthetic", "minimum_tests": 1,
    } for index in range(5)]
    cases_path, rates_path = tmp_path / "cases.json", tmp_path / "rates.json"
    cases_path.write_text(json.dumps({"cases": cases}))
    rates_path.write_text(json.dumps({"rates": {MODEL: {"input": 1.0, "output": 3.0}}}))
    args = argparse.Namespace(
        cases=cases_path, rate_card=rates_path, output=tmp_path / "series",
        expected_commit=COMMIT, rounds=3, max_estimated_inference_usd=10.0,
    )
    state = SimpleNamespace(records=[], mutate=lambda index, summary: None)

    async def execute(repo_url, output, *, project_path):
        index = len(state.records) + 1
        # Deliberately failed synthetic runs still consume observed inference.
        # The runner must preserve them and enforce its budget regardless of success.
        summary = {
            "id": f"{index:012x}", "mode": "live", "status": "failed",
            "repo_url": repo_url, "project_path": project_path, "model_id": MODEL,
            "created_at": "2026-09-10T00:00:00+00:00",
            "updated_at": "2026-09-10T00:00:01+00:00",
            "baseline_commit_sha": COMMIT, "branches": [], **source,
            "runtime_config_digest": CONFIG,
            "failure_reason": "Synthetic test result; no real provider was called",
            "provider_usage": {
                "model_usage_version": 1, "requests": 1, "responses_with_usage": 1,
                "input_tokens": 250_000, "output_tokens": 0,
            },
        }
        state.mutate(index, summary)
        output.mkdir(parents=True)
        raw = (json.dumps(summary, indent=2) + "\n").encode()
        result_path = output / f"{summary['id']}.json"
        result_path.write_bytes(raw)
        state.records.append((result_path, raw))
        return 1

    execute_spy = Mock(side_effect=execute)
    monkeypatch.setattr(runner, "execute", execute_spy)
    return SimpleNamespace(
        runner=runner, args=args, state=state, source=source, source_lookup=source_lookup,
        remote_lookup=remote_lookup, execute=execute_spy,
    )


def assert_retained(case, count):
    attempts = json.loads((case.args.output / "attempts.json").read_text())["attempts"]
    report = json.loads((case.args.output / "results.json").read_text())
    assert len(attempts) == len(case.state.records) == case.execute.call_count == count
    assert report["live_terminal_attempts"] == count
    assert report["qualified_successes"] == 0
    assert (case.args.output / "series-plan.json").is_file()
    assert (case.args.output / "results.md").is_file()
    for attempt, (path, original) in zip(attempts, case.state.records, strict=True):
        assert case.args.output / attempt["path"] == path
        assert path.read_bytes() == original
    return report


async def test_budget_reached_stops_before_starting_another_run(runner_case):
    runner_case.args.max_estimated_inference_usd = 0.5
    with pytest.raises(ValueError, match="ceiling reached"):
        await runner_case.runner.run(runner_case.args)
    report = assert_retained(runner_case, 2)
    assert report["series"]["estimated_reported_inference_usd"] == 0.5
    assert report["series"]["reported_usage_covers_all_model_requests"] is True
    assert not (runner_case.args.output / "round-01" / "case-2").exists()


@pytest.mark.parametrize("missing", ["all_usage", "response_coverage"])
async def test_missing_usage_stops_and_retains_the_uncertain_attempt(runner_case, missing):
    def mutate(index, summary):
        if index == 2:
            if missing == "all_usage":
                summary.pop("provider_usage")
            else:
                summary["provider_usage"].pop("responses_with_usage")

    runner_case.state.mutate = mutate
    with pytest.raises(ValueError, match="incomplete usage"):
        await runner_case.runner.run(runner_case.args)
    report = assert_retained(runner_case, 2)
    assert report["series"]["reported_usage_covers_all_model_requests"] is False
    assert not (runner_case.args.output / "round-01" / "case-2").exists()


async def test_nonempty_output_is_rejected_without_touching_existing_evidence(runner_case):
    runner_case.args.output.mkdir()
    existing = runner_case.args.output / "attempts.json"
    original = b'{"synthetic_existing_evidence": true}\n'
    existing.write_bytes(original)
    with pytest.raises(ValueError, match="Output is not empty"):
        await runner_case.runner.run(runner_case.args)
    assert existing.read_bytes() == original
    assert list(runner_case.args.output.iterdir()) == [existing]
    runner_case.execute.assert_not_called()
    runner_case.remote_lookup.assert_not_called()
    runner_case.source_lookup.assert_not_called()


@pytest.mark.parametrize("drift", ["local_source", "remote_head", "recorded_runtime"])
async def test_version_drift_stops_without_discarding_completed_results(runner_case, drift):
    if drift == "local_source":
        runner_case.source_lookup.side_effect = [
            dict(runner_case.source), dict(runner_case.source),
            {**runner_case.source, "orchestrator_digest": "e" * 64},
        ]
    elif drift == "remote_head":
        runner_case.remote_lookup.side_effect = [f"{COMMIT}\tHEAD\n", f"{'e' * 40}\tHEAD\n"]
    else:
        def mutate(index, summary):
            if index == 2:
                summary["runtime_config_digest"] = "e" * 64

        runner_case.state.mutate = mutate
    with pytest.raises(ValueError, match="Source changed|Recorded provenance differs"):
        await runner_case.runner.run(runner_case.args)
    count = 2 if drift == "recorded_runtime" else 1
    report = assert_retained(runner_case, count)
    assert report["series"]["all_recorded_runtime_fingerprints_match_plan"] is (
        drift != "recorded_runtime"
    )
    assert not (runner_case.args.output / "round-01" / f"case-{count}").exists()
