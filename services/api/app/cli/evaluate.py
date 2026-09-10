"""Summarize retained migration JSON locally; never execute providers or open a run DB."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

STRATEGIES = {"minimal", "compatibility", "refactor"}
TERMINAL = {"completed", "failed", "cancelled"}
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")


def _count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _text(value: object) -> str:
    """Only identifiers are copied into the aggregate, never diagnostics or patches."""
    return value if isinstance(value, str) and re.fullmatch(r"[\w./:@+-]{1,200}", value) else ""


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("A retained run is missing its timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Run timestamps must include a timezone")
    return result


def _failure_category(run: dict[str, Any]) -> str:
    reason = str(run.get("failure_reason", "")).lower()
    for label, words in (
        ("syntax", ("syntax", "indentation", "compile")),
        ("timeout", ("timeout", "time limit", "timed out")),
        ("baseline", ("baseline",)),
        ("patch", ("patch", "diff")),
        ("model", ("model", "nebius request", "structured")),
        ("interrupted", ("stopped", "cancel")),
    ):
        if any(word in reason for word in words):
            return label
    return "recorded failure" if run.get("status") in {"failed", "cancelled"} else "none"


def assess(run: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    branches = run.get("branches") or []
    if not isinstance(branches, list) or not all(isinstance(b, dict) for b in branches):
        raise ValueError("Run branches must be a list of objects")
    winners = [b for b in branches if b.get("strategy_id") == run.get("winner_id")]
    winner = winners[0] if len(winners) == 1 else {}
    revalidation = run.get("revalidation") or {}
    if not isinstance(revalidation, dict):
        raise ValueError("Run revalidation must be an object")
    minimum = case["minimum_tests"]
    baseline_tests = _count(run.get("baseline_tests_collected"))
    tests = _count(winner.get("tests_collected"))
    checkpoint = _text(run.get("revalidated_checkpoint_id"))
    baseline_checkpoint = _text(run.get("baseline_checkpoint_id"))
    gates = {
        "live_completed": run.get("mode") == "live" and run.get("status") == "completed",
        "pinned_baseline": bool(SHA.fullmatch(str(run.get("baseline_commit_sha", "")))),
        "baseline_contract": bool(
            DIGEST.fullmatch(str(run.get("baseline_test_contract_digest", "")))
        ),
        "baseline_test_count": baseline_tests is not None and baseline_tests >= minimum,
        "three_results": len(branches) == 3
        and {b.get("strategy_id") for b in branches} == STRATEGIES,
        "nvidia_model": _text(run.get("model_id")).lower().startswith("nvidia/"),
        "winner_passed": winner.get("status") == "passed",
        "test_contract_preserved": winner.get("test_contract_preserved") is True,
        "pydantic_2": _count(winner.get("pydantic_major")) == 2,
        "tests_pass": tests is not None and baseline_tests is not None
        and tests >= max(minimum, baseline_tests)
        and _count(winner.get("tests_passed")) == tests
        and _count(winner.get("tests_failed")) == 0
        and _count(winner.get("test_exit_code")) == 0,
        "dependencies_pass": winner.get("pip_check_passed") is True
        and _count(winner.get("pip_exit_code")) == 0,
        "patch_retained": winner.get("patch_applicable") is True
        and isinstance(run.get("patch"), str) and bool(run["patch"].strip()),
        "revalidation_recorded": bool(checkpoint and baseline_checkpoint)
        and checkpoint not in {baseline_checkpoint, winner.get("checkpoint_id")},
        "revalidation_pass": revalidation.get("status") == "passed"
        and revalidation.get("checkpoint_id") == checkpoint
        and revalidation.get("strategy_id") == run.get("winner_id")
        and revalidation.get("patch") == run.get("patch")
        and revalidation.get("patch_applicable") is True
        and revalidation.get("test_contract_preserved") is True
        and _count(revalidation.get("pydantic_major")) == 2
        and _count(revalidation.get("tests_collected")) == tests
        and _count(revalidation.get("tests_passed")) == tests
        and _count(revalidation.get("tests_failed")) == 0
        and _count(revalidation.get("test_exit_code")) == 0
        and _count(revalidation.get("pip_exit_code")) == 0
        and revalidation.get("pip_check_passed") is True,
    }
    expected_repo = case.get("public_repo_url")
    gates["case_public_source"] = isinstance(expected_repo, str) and bool(expected_repo) and (
        str(run.get("repo_url", "")).rstrip("/").removesuffix(".git")
        == expected_repo.rstrip("/").removesuffix(".git")
    )
    # Old controlled-fixture exports predate the project_path field.
    project_path = run.get("project_path") or (
        "fixtures/pydantic-v1-app" if str(run.get("repo_url", "")).rstrip("/")
        .removesuffix(".git") == "https://github.com/jsdhwfmax/branchshift-ai" else "."
    )
    gates["case_project_path"] = project_path == case.get("project_path", ".")
    created, updated = _timestamp(run.get("created_at")), _timestamp(run.get("updated_at"))
    duration = (updated - created).total_seconds()
    if duration < 0:
        raise ValueError("Run updated_at precedes created_at")
    usage = run.get("provider_usage") or {}
    if not isinstance(usage, dict):
        raise ValueError("provider_usage must be an object")
    child_ids = [_text(b.get("checkpoint_id")) for b in branches]
    return {
        "run_id": _text(run.get("id")), "case_id": case["id"],
        "created_at": created.isoformat(), "mode": _text(run.get("mode")),
        "status": _text(run.get("status")), "model_id": _text(run.get("model_id")),
        "baseline_commit_sha": _text(run.get("baseline_commit_sha")),
        "project_path": _text(project_path),
        "qualified_success": all(gates.values()), "gates": gates,
        "failure_category": _failure_category(run),
        "ledger_duration_seconds": round(duration, 3),
        "winner_id": _text(run.get("winner_id")),
        "baseline_tests": baseline_tests, "winner_tests": tests,
        "winner_pydantic_major": _count(winner.get("pydantic_major")),
        "three_distinct_child_ids_recorded": len(child_ids) == 3
        and all(child_ids) and len(set(child_ids)) == 3
        and baseline_checkpoint not in child_ids,
        "observed_model_requests": _count(usage.get("requests")),
        "observed_input_tokens": _count(usage.get("input_tokens")),
        "observed_output_tokens": _count(usage.get("output_tokens")),
        "sandbox_operations": None, "total_cost_usd": None,
    }


def aggregate(cases: list[dict[str, Any]], attempts: list[dict[str, Any]],
              base: Path) -> dict[str, Any]:
    case_map = {case["id"]: case for case in cases}
    distinct_paths = {(case.get("public_repo_url"), case.get("project_path")) for case in cases}
    if len(case_map) != len(cases) or len(distinct_paths) != len(cases) or any(
        not _text(case["id"]) or type(case.get("minimum_tests")) is not int
        or case["minimum_tests"] < 1 for case in cases
    ):
        raise ValueError("Cases require unique IDs and positive minimum test counts")
    rows = []
    seen: set[str] = set()
    for attempt in attempts:
        if attempt.get("case_id") not in case_map:
            raise ValueError("Attempt refers to an unknown case")
        raw = (base / attempt["path"]).read_bytes()
        document = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError("Retained JSON must be an object")
        run = document.get("run", document)
        if not isinstance(run, dict):
            raise ValueError("Retained run must be an object")
        row = assess(run, case_map[attempt["case_id"]])
        if not row["run_id"] or row["run_id"] in seen:
            raise ValueError(
                "Run IDs must be nonempty and unique; duplicate exports are not attempts"
            )
        seen.add(row["run_id"])
        for field in ("orchestrator_revision", "orchestrator_digest", "runtime_config_digest"):
            value = _text(run.get(field) or attempt.get(field))
            pattern = SHA if field == "orchestrator_revision" else DIGEST
            row[field] = value if pattern.fullmatch(value) else ""
        dirty = run.get("orchestrator_dirty", attempt.get("orchestrator_dirty"))
        row["orchestrator_dirty"] = dirty if type(dirty) is bool else None
        row["source_json_sha256"] = hashlib.sha256(raw).hexdigest()
        rows.append(row)
    rows.sort(key=lambda row: (_timestamp(row["created_at"]), row["run_id"]))
    summaries = []
    for case in cases:
        case_rows = [row for row in rows if row["case_id"] == case["id"]]
        streak, key = 0, None
        for row in case_rows:
            current_key = (
                row["baseline_commit_sha"], row["project_path"], row["model_id"],
                row["orchestrator_digest"], row["runtime_config_digest"],
            )
            eligible = row["qualified_success"] and row["orchestrator_digest"] \
                and row["runtime_config_digest"]
            streak = (streak + 1 if key == current_key else 1) if eligible else 0
            key = current_key if eligible else None
        terminal = [r for r in case_rows if r["mode"] == "live" and r["status"] in TERMINAL]
        successes = sum(r["qualified_success"] for r in terminal)
        summaries.append({
            "case_id": case["id"], "attempts": len(case_rows),
            "live_terminal_attempts": len(terminal), "qualified_successes": successes,
            "success_fraction": successes / len(terminal) if terminal else None,
            "trailing_same_runtime_successes": streak,
        })
    live = [r for r in rows if r["mode"] == "live" and r["status"] in TERMINAL]
    durations = sorted(r["ledger_duration_seconds"] for r in live)
    tokens = {}
    for field in ("observed_model_requests", "observed_input_tokens", "observed_output_tokens"):
        known = [r[field] for r in live if r[field] is not None]
        tokens[field] = {"sum": sum(known) if known else None, "records_with_field": len(known)}
    return {
        "schema_version": 1, "evidence_scope": "local aggregation of supplied retained JSON",
        "attempt_count": len(rows), "live_terminal_attempts": len(live),
        "qualified_successes": sum(r["qualified_success"] for r in live),
        "independent_cases_with_success": sum(c["qualified_successes"] > 0 for c in summaries),
        "five_cases_pass": len(summaries) >= 5
        and all(c["qualified_successes"] > 0 for c in summaries),
        "three_consecutive_pass": any(
            c["trailing_same_runtime_successes"] >= 3 for c in summaries
        ),
        "three_successes_per_case": len(summaries) >= 5
        and all(c["qualified_successes"] >= 3 for c in summaries),
        "median_ledger_seconds": median(durations) if durations else None,
        "p95_ledger_seconds": durations[math.ceil(len(durations) * .95) - 1] if durations else None,
        "observed_usage": tokens, "total_cost_usd": None, "sandbox_operations": None,
        "cases": summaries, "attempts": rows,
    }


def render(report: dict[str, Any]) -> str:
    def cell(value: object) -> str:
        return "unknown" if value is None else str(value).replace("|", "\\|")

    lines = [
        "# Retained migration evaluation", "",
        "Generated locally from the explicitly supplied export manifest. No providers were called.",
        "The manifest must include failed attempts; this tool cannot discover omitted runs.", "",
        f"Qualified successes: {report['qualified_successes']} / "
        f"{report['live_terminal_attempts']} terminal live attempts.",
        f"Independent cases with success: {report['independent_cases_with_success']}; "
        f"five-case gate: {report['five_cases_pass']}; "
        f"three-consecutive gate: {report['three_consecutive_pass']}.", "",
        f"At least three qualified successes on every case: {report['three_successes_per_case']}.",
        "",
        "| Case | Attempts | Live terminal | Qualified success | Trailing same-runtime streak |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for case in report["cases"]:
        lines.append("| " + " | ".join(cell(case[field]) for field in (
            "case_id", "attempts", "live_terminal_attempts", "qualified_successes",
            "trailing_same_runtime_successes",
        )) + " |")
    lines += [
        "", "| Run | Case | Status | Winner | Qualified | Unmet gates | Input/output tokens |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["attempts"]:
        missing = ", ".join(name for name, passed in row["gates"].items() if not passed) or "none"
        lines.append("| " + " | ".join(cell(item) for item in (
            row["run_id"], row["case_id"], row["status"], row["winner_id"],
            row["qualified_success"], missing,
            f"{cell(row['observed_input_tokens'])} / {cell(row['observed_output_tokens'])}",
        )) + " |")
    lines += ["", f"Median ledger duration: {cell(report['median_ledger_seconds'])} seconds. "
              f"p95: {cell(report['p95_ledger_seconds'])} seconds (nearest rank).",
              "Durations include queue time and final writes; small-sample p95 is descriptive.",
              "", "Observed model usage (response-reported totals, not complete billing):"]
    for name, metric in report["observed_usage"].items():
        lines.append(f"- {name}: {cell(metric['sum'])}; field present in "
                     f"{metric['records_with_field']} terminal live records.")
    lines += ["", "Total cost and Sandbox operation counts: **unknown**, not zero.",
              "Revalidation is a retained-ledger assertion; this tool does not replay the patch "
              "or independently authenticate provider evidence.",
              "Streaks require the same case/path, baseline commit, NVIDIA model, orchestrator "
              "content digest and runtime-config digest. Dirty state is disclosed, not excluded.",
              ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="Markdown path; paired JSON also written"
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    if args.output.suffix != ".md":
        parser.error("--output must end in .md")
    try:
        report = aggregate(json.loads(args.cases.read_text())["cases"],
                           json.loads(args.attempts.read_text())["attempts"], args.attempts.parent)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(
            f"Cannot aggregate retained evidence ({type(exc).__name__}); check input schema"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(report))
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"REPORT={args.output.resolve()}")
    raise SystemExit(1 if args.require_complete and not (
        report["five_cases_pass"] and report["three_consecutive_pass"]
    ) else 0)


if __name__ == "__main__":
    main()
