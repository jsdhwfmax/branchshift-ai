"""Validate a predeclared complete-case series and estimate reported inference usage."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.cli.evaluate import TERMINAL, aggregate


def estimate_inference(run: dict[str, Any], rates: dict[str, Any]) -> dict[str, Any]:
    usage = run.get("provider_usage") or {}
    if not isinstance(usage, dict):
        raise ValueError("Usage must be an object")
    model_id = run.get("model_id")
    rate = rates.get(model_id) if isinstance(model_id, str) else None
    if rate is not None and (not isinstance(rate, dict) or any(
        type(rate.get(name)) not in (int, float) or not math.isfinite(rate[name])
        or rate[name] < 0 for name in ("input", "output")
    )):
        raise ValueError("Rate card must contain finite nonnegative token prices")
    names = ("input_tokens", "output_tokens", "requests", "responses_with_usage")
    counts: dict[str, Any] = {name: usage.get(name) for name in names}
    valid_tokens = all(type(counts[n]) is int and counts[n] >= 0 for n in names[:2])
    complete = type(usage.get("model_usage_version")) is int \
        and usage["model_usage_version"] == 1 and all(
        type(counts[n]) is int and counts[n] >= 0 for n in names
    ) and counts["requests"] == counts["responses_with_usage"]
    estimate = None
    if rate and valid_tokens:
        estimate = round((counts["input_tokens"] * rate["input"]
                          + counts["output_tokens"] * rate["output"]) / 1_000_000, 8)
    return {
        "estimated_reported_inference_usd": estimate,
        "reported_usage_covers_all_model_requests": bool(complete),
        "model_requests": counts["requests"],
        "responses_with_usage": counts["responses_with_usage"],
        "scope": "response-reported inference only; excludes tax and other services",
    }


def summarize_series(plan: dict[str, Any], attempts: list[dict[str, Any]],
                     base: Path, rate_card: dict[str, Any]) -> dict[str, Any]:
    cases, rounds = plan["cases"], plan["rounds"]
    if type(rounds) is not int or rounds < 1:
        raise ValueError("Series rounds must be a positive integer")
    expected = {(round_id, case["id"]) for round_id in range(1, rounds + 1) for case in cases}
    slots = [(attempt["round"], attempt["case_id"]) for attempt in attempts]
    if len(slots) != len(set(slots)) or any(slot not in expected for slot in slots):
        raise ValueError("Series attempts contain duplicate or unplanned round/case slots")
    report = aggregate(cases, attempts, base)
    run_rows = {row["run_id"]: row for row in report["attempts"]}
    costs = []
    comparisons = []
    for attempt in attempts:
        document = json.loads((base / attempt["path"]).read_text())
        run = document.get("run", document)
        row = run_rows[run["id"]]
        row["round"] = attempt["round"]
        estimate = estimate_inference(run, rate_card["rates"])
        row.update(estimate)
        costs.append(estimate)
        comparisons.append({
            "runtime": all(run.get(key) == plan[key] for key in (
                "orchestrator_digest", "runtime_config_digest", "model_id",
            )),
            "baseline": run.get("baseline_commit_sha") == plan["baseline_commit_sha"],
        })
    terminal = all(row["mode"] == "live" and row["status"] in TERMINAL
                   for row in report["attempts"])
    amounts = [cost["estimated_reported_inference_usd"] for cost in costs]
    report["series"] = {
        "planned_rounds": rounds,
        "planned_attempts": len(expected),
        "recorded_attempts": len(attempts),
        "all_planned_slots_have_terminal_live_results": set(slots) == expected and terminal,
        "all_recorded_runtime_fingerprints_match_plan": bool(comparisons)
        and all(item["runtime"] for item in comparisons),
        "all_recorded_baselines_match_plan": bool(comparisons)
        and all(item["baseline"] for item in comparisons),
        "missing_slots": [
            {"round": round_id, "case_id": case_id}
            for round_id, case_id in sorted(expected - set(slots))
        ],
        "estimated_reported_inference_usd": round(sum(amounts), 8)
        if amounts and all(amount is not None for amount in amounts) else None,
        "reported_usage_covers_all_model_requests": bool(costs) and all(
            cost["reported_usage_covers_all_model_requests"] for cost in costs
        ),
        "rate_card": rate_card,
    }
    return report
