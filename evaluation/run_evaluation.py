"""Run a declared five-case matrix with real providers; all outcomes are retained.

This command uses existing configured inference credits. It refuses to overwrite
an output directory or silently retry a completed or uncertain attempt.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.cli.evaluate import render
from app.cli.live_run import execute
from app.cli.series import estimate_inference, summarize_series
from app.config import settings
from app.domain.models import CreateRunRequest
from app.provenance import runtime_config_digest, source_provenance


def write_json(path: Path, data: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


async def run(args: argparse.Namespace) -> int:
    cases = json.loads(args.cases.read_text())["cases"]
    rate_card = json.loads(args.rate_card.read_text())
    if len(cases) < 5 or settings.nemotron_model not in rate_card["rates"]:
        raise ValueError("Require at least five cases and an applicable model rate card")
    estimate_inference({"model_id": settings.nemotron_model}, rate_card["rates"])
    if args.rounds < 3 or not math.isfinite(args.max_estimated_inference_usd) \
            or args.max_estimated_inference_usd <= 0:
        raise ValueError("Require at least three rounds and a positive inference budget")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Case IDs must be unique")
    for case in cases:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,50}", case["id"]):
            raise ValueError("Case IDs must be simple identifiers")
        CreateRunRequest.model_validate({
            "repo_url": case["public_repo_url"], "project_path": case["project_path"],
        })
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit):
        raise ValueError("Expected public commit must be a full SHA")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Output is not empty; inspect retained state before a new series")
    if not settings.nebius_api_key or not settings.tavily_api_key or not settings.nebius_project_id:
        raise ValueError("Live provider configuration is incomplete")
    provenance = source_provenance()
    plan = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rounds": args.rounds, "cases": cases,
        "baseline_commit_sha": args.expected_commit,
        "model_id": settings.nemotron_model,
        "runtime_config_digest": runtime_config_digest(replace(settings, mode="live")),
        **provenance,
        "max_estimated_inference_usd": args.max_estimated_inference_usd,
        "budget_scope": "stop between runs on reported estimate or incomplete usage; not an invoice",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "series-plan.json", plan)
    attempts: list[dict[str, object]] = []
    for round_id in range(1, args.rounds + 1):
        for case in cases:
            remote_result = await asyncio.to_thread(subprocess.check_output,
                ["git", "ls-remote", case["public_repo_url"], "HEAD"], text=True, timeout=30)
            remote = remote_result.split()[0]
            current_source = await asyncio.to_thread(source_provenance)
            if remote != args.expected_commit or current_source["orchestrator_digest"] \
                    != plan["orchestrator_digest"]:
                raise ValueError("Source changed during the declared series; retained work is intact")
            case_output = args.output / f"round-{round_id:02d}" / case["id"]
            print(f"ROUND={round_id} CASE={case['id']}", flush=True)
            await execute(case["public_repo_url"], case_output, project_path=case["project_path"])
            summaries = [path for path in case_output.glob("*.json")
                         if re.fullmatch(r"[0-9a-f]{12}", path.stem)]
            if len(summaries) != 1:
                raise ValueError("Expected exactly one retained result; inspect before any retry")
            attempts.append({
                "round": round_id, "case_id": case["id"],
                "path": str(summaries[0].relative_to(args.output)),
            })
            write_json(args.output / "attempts.json", {"schema_version": 1, "attempts": attempts})
            report = summarize_series(plan, attempts, args.output, rate_card)
            write_json(args.output / "results.json", report)
            (args.output / "results.md").write_text(render(report) + "\n## Declared series\n\n"
                + "```json\n" + json.dumps(report["series"], indent=2) + "\n```\n")
            series = report["series"]
            print("SERIES_PROGRESS=" + json.dumps({
                "terminal": len(attempts), "qualified": report["qualified_successes"],
                "reported_inference_usd": series["estimated_reported_inference_usd"],
            }), flush=True)
            latest = json.loads(summaries[0].read_text())
            if not series["all_recorded_runtime_fingerprints_match_plan"] or (
                latest.get("baseline_commit_sha") is not None
                and latest["baseline_commit_sha"] != args.expected_commit
            ):
                raise ValueError("Recorded provenance differs from plan; inspect retained evidence")
            if not series["reported_usage_covers_all_model_requests"]:
                raise ValueError("A model request has incomplete usage; budget evidence needs review")
            if series["estimated_reported_inference_usd"] >= args.max_estimated_inference_usd:
                raise ValueError("Declared inference estimate ceiling reached; no further runs started")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--cases", type=Path, default=root / "cases.json")
    parser.add_argument("--rate-card", type=Path, default=root / "pricing-20260910.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-estimated-inference-usd", type=float, default=3.0)
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"SERIES_STOPPED={type(exc).__name__}: {exc}", flush=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
