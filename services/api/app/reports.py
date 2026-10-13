"""Deterministic presentation of retained evidence; no providers or history writes."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.domain.models import (
    TERMINAL_RUN_STATUSES,
    BranchResult,
    BranchStatus,
    RunEvent,
    RunStatus,
    RunSummary,
)
from app.orchestrator.behavior_probes import BehaviorProbeResults

UNKNOWN = "Unknown (not recorded)"


def _probe_review(run: RunSummary) -> list[str]:
    lines = ["## Explicit behavior review", ""]
    if run.behavior_probes is None:
        return lines + ["No optional input examples were requested for this run.", ""]
    lines += [
        "These fixed model inputs are an additional maintainer review, not a migration "
        "acceptance gate or proof of general behavior equivalence. Differences require "
        "review even when the original test suite passes. A rejected input records only "
        "its exception class; error messages and side effects are not compared.", "",
    ]

    def observation(results: BehaviorProbeResults | None, case_id: str) -> str:
        item = next((item for item in results.observations if item.id == case_id), None) \
            if results else None
        if item is None:
            return UNKNOWN
        if item.status == "accepted":
            value = json.dumps(item.value, sort_keys=True, ensure_ascii=True)
            return "accepted: " + value[:600] + ("… (see JSON export)" if len(value) > 600 else "")
        return item.status + ": " + str(item.error_type or item.reason)

    for case in run.behavior_probes.cases:
        lines += [f"### Example {_text(case.id)}", ""] + _table([
            ("Model", f"{case.module}.{case.model}"),
            ("Baseline observation", observation(run.baseline_probe_results, case.id)),
        ])
        for candidate in [*run.branches, *([run.revalidation] if run.revalidation else [])]:
            label = "Clean revalidation" if candidate is run.revalidation else candidate.strategy_id
            comparison = candidate.behavior_probe_comparison
            finding = next((item for item in comparison.cases if item.id == case.id), None) \
                if comparison else None
            lines += _table([
                (f"{label} observation", observation(candidate.behavior_probe_results, case.id)),
                (f"{label} review", f"{finding.status}: {finding.basis}" if finding else None),
                (f"{label} unavailable detail", candidate.behavior_probe_error),
            ])
    if run.baseline_probe_error:
        lines += ["Baseline review unavailable: " + _text(run.baseline_probe_error), ""]
    return lines


def _recorded(model: BaseModel, name: str) -> object:
    return getattr(model, name) if name in model.model_fields_set else None


def _text(value: object) -> str:
    if value is None:
        return UNKNOWN
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, datetime):
        value = value.isoformat()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.3f}" if math.isfinite(value) else "Unknown (non-finite value)"
    raw = str(value).replace("\r\n", "\n").replace("\r", "\n")
    raw = "".join(
        " ↵ "
        if char == "\n"
        else f"\\u{ord(char):04x}"
        if unicodedata.category(char).startswith("C")
        else char
        for char in raw
    )
    # HTML, links/images, table separators, headings and control characters are data.
    return re.sub(r"([\\`*_\[\]{}()#+.!|>~-])", r"\\\1", html.escape(raw, quote=True))


def _table(rows: Sequence[tuple[str, object]]) -> list[str]:
    return (
        ["| Field | Recorded value |", "| --- | --- |"]
        + [f"| {label} | {_text(value)} |" for label, value in rows]
        + [""]
    )


def _passed_candidate(result: BranchResult) -> bool:
    # The documented selection pool, not proof that a live migration was revalidated.
    return (
        _recorded(result, "patch_applicable") is True
        and result.status is BranchStatus.PASSED
        and result.tests_collected > 0
        and result.tests_failed == 0
        and result.pip_check_passed
    )


def _comparison(run: RunSummary) -> tuple[list[str], bool]:
    if not run.winner_id:
        return ["No winner is recorded.", ""], False
    winners = [branch for branch in run.branches if branch.strategy_id == run.winner_id]
    if len(winners) != 1 or len({b.strategy_id for b in run.branches}) != len(run.branches):
        return ["Recorded winner has missing or conflicting candidate evidence.", ""], False
    winner = winners[0]
    lines = [f"Recorded winner: {_text(run.winner_id)}.", ""]
    consistent = _passed_candidate(winner)
    if not consistent:
        lines += ["The recorded winner does not meet the passed-candidate selection gate.", ""]
    for other in run.branches:
        if other is winner:
            continue
        prefix = f"{_text(winner.strategy_id)} versus {_text(other.strategy_id)}: "
        if not other.patch_applicable or (
            _passed_candidate(winner) and not _passed_candidate(other)
        ):
            lines.append(prefix + "the other candidate did not meet the passed-candidate gate.")
            continue
        dimensions: list[tuple[str, object, object, bool]] = [
            ("test pass ratio", winner.pass_ratio, other.pass_ratio, True),
            ("dependency consistency", winner.pip_check_passed, other.pip_check_passed, True),
            ("lint findings", winner.lint_findings, other.lint_findings, False),
            ("changed lines", winner.changed_lines, other.changed_lines, False),
            ("elapsed seconds", winner.elapsed_seconds, other.elapsed_seconds, False),
            ("strategy ID", winner.strategy_id, other.strategy_id, False),
        ]
        for name, own, theirs, higher in dimensions:
            if own == theirs:
                continue
            # Each pair has the same comparable type, from the fixed model fields above.
            supported = own > theirs if higher else own < theirs  # type: ignore[operator]
            consistent = consistent and supported
            lines.append(
                prefix
                + f"{name} is {_text(own)} versus {_text(theirs)}; "
                + (
                    "this supports the stored selection."
                    if supported
                    else "this conflicts with the stored selection; it has not been replaced."
                )
            )
            if name == "lint findings" and winner.changed_lines > other.changed_lines:
                lines.append(
                    f"Lint precedes patch size: the selected patch is larger "
                    f"({winner.changed_lines} versus {other.changed_lines} changed lines)."
                )
            break
    return lines + [""], consistent


def _live_checks(result: BranchResult | None, run: RunSummary) -> bool:
    original_tests_pass = bool(
        result is not None and (
            result.tests_passed == result.tests_collected and (result.tests_skipped or 0) == 0
            if run.baseline_tests_passed is None and run.baseline_tests_skipped is None else
            result.test_outcomes_preserved is True
            and result.tests_collected == run.baseline_tests_collected
            and run.baseline_tests_passed is not None
            and run.baseline_tests_skipped is not None
            and (
                run.baseline_tests_passed + run.baseline_tests_skipped
                == run.baseline_tests_collected
            )
            and result.tests_passed >= run.baseline_tests_passed
            and result.tests_skipped is not None
            and result.tests_passed + result.tests_skipped == result.tests_collected
        )
    )
    return bool(
        result is not None
        and _passed_candidate(result)
        and original_tests_pass
        and result.test_outcomes_preserved is not False
        and run.baseline_tests_collected is not None
        and result.tests_collected == run.baseline_tests_collected
        and result.pydantic_major == 2
        and result.test_exit_code == 0
        and result.pip_exit_code == 0
        and result.test_contract_preserved is True
        and result.checkpoint_id
        and result.patch
    )


def _usage(run: RunSummary) -> list[str]:
    usage = run.provider_usage

    def valid(name: str) -> bool:
        return name in usage and type(usage[name]) is int and usage[name] >= 0

    model_names = ("requests", "responses_with_usage", "input_tokens", "output_tokens")
    if usage.get("model_usage_version") != 1 or not all(valid(n) for n in model_names):
        coverage = "Unknown: complete versioned model-usage evidence is not recorded."
    elif usage["requests"] != usage["responses_with_usage"]:
        coverage = "Incomplete: not every attempted model request has response usage."
    else:
        coverage = (
            "All recorded model requests have response usage; this is not invoice verification."
        )
    lines = ["## Usage and coverage", "", coverage, ""] + _table(
        [
            ("Model usage version", usage.get("model_usage_version")),
            ("Attempted model requests", usage.get("requests")),
            ("Responses with usage", usage.get("responses_with_usage")),
            ("Reported input tokens", usage.get("input_tokens")),
            ("Reported output tokens", usage.get("output_tokens")),
        ]
    )
    outcomes = ("attempted", "completed", "failed", "cancelled")
    operations = ("sdk_calls", "image_use", "run", "read")
    names = [f"sandbox_{op}_{outcome}" for op in operations for outcome in outcomes]
    complete = usage.get("sandbox_usage_version") == 1 and all(valid(n) for n in names)
    balanced = (
        complete
        and all(
            usage[f"sandbox_{op}_attempted"]
            == sum(usage[f"sandbox_{op}_{outcome}"] for outcome in outcomes[1:])
            for op in operations
        )
        and all(
            usage[f"sandbox_sdk_calls_{outcome}"]
            == sum(usage[f"sandbox_{op}_{outcome}"] for op in operations[1:])
            for outcome in outcomes
        )
    )
    if balanced and run.status in TERMINAL_RUN_STATUSES:
        lines += ["Sandbox SDK counters are versioned and internally settled.", ""]
    else:
        lines += ["Sandbox SDK coverage is unknown or unsettled; absent counters are not zero.", ""]
    lines += [
        "| Adapter call | Attempted | Completed | Failed | Cancelled |",
        "| --- | --- | --- | --- | --- |",
    ]
    for operation in operations:
        values = " | ".join(_text(usage.get(f"sandbox_{operation}_{o}")) for o in outcomes)
        lines.append(f"| {_text(operation)} | {values} |")
    lines += [
        "",
        "SDK invocations are not internal HTTP requests or billed Sandbox operations.",
        "A returned nonzero process exit still completes an SDK call; failed/cancelled calls "
        "have an uncertain remote outcome.",
        "",
        "Monetary/credit cost is not established by this export. No absent cost, "
        "unmatched model rate, or unreported service charge is replaced with zero.",
        "",
    ]
    return lines


def render_markdown_report(run: RunSummary, events: Sequence[RunEvent]) -> str:
    """Render stored fields only. Never rerun providers, select a new winner or save state."""
    if any(event.run_id != run.id for event in events):
        raise ValueError("Report events must belong to the selected run")
    comparison, selection_consistent = _comparison(run)
    winner = next((b for b in run.branches if b.strategy_id == run.winner_id), None)
    revalidation = run.revalidation
    clean = bool(
        _live_checks(revalidation, run)
        and revalidation is not None
        and revalidation.strategy_id == run.winner_id
        and revalidation.patch == run.patch
        and revalidation.checkpoint_id == run.revalidated_checkpoint_id
        and revalidation.checkpoint_id
        not in {run.baseline_checkpoint_id, *(branch.checkpoint_id for branch in run.branches)}
    )
    supported = bool(
        run.mode == "live"
        and run.status is RunStatus.COMPLETED
        and selection_consistent
        and run.model_id
        and run.baseline_commit_sha
        and run.baseline_checkpoint_id
        and run.baseline_test_contract_digest
        and {b.strategy_id for b in run.branches} == {"minimal", "compatibility", "refactor"}
        and _live_checks(winner, run)
        and winner is not None
        and winner.patch == run.patch
        and clean
    )
    scope = "Live provider record" if run.mode == "live" else "Illustrative sample (mock mode)"
    lines = [
        f"# BranchShift evidence report: {_text(run.id)}",
        "",
        scope + ".",
        "",
        "Deterministic summary of stored evidence. No model generated this explanation, "
        "and this export did not replay checks or independently authenticate "
        "provider records.",
        "The JSON report remains the full machine-readable record. Durations below are "
        "rounded to three decimal places.",
        "Verification scope: the repository's existing test suite, test-contract integrity, "
        "dependency consistency and recorded Pydantic runtime. Passing these checks does "
        "not establish behavior equivalence for untested inputs, coercion, validation "
        "errors or serialization. Maintainer review and additional behavior tests may "
        "still be needed.",
        "",
    ]
    if supported:
        lines += [
            "Stored live winner and clean-revalidation evidence satisfy the reporting gates.",
            "",
        ]
    else:
        lines += [
            "Successful live migration is not established by this record's reporting gates.",
            "",
        ]
    lines += _table(
        [
            ("Run status", run.status),
            ("Failure reason", run.failure_reason),
            ("Repository", run.repo_url),
            ("Project directory", run.project_path),
            ("Target", _recorded(run, "target")),
            ("Created", _recorded(run, "created_at")),
            ("Last saved", _recorded(run, "updated_at")),
            ("Exact model ID", run.model_id),
            ("Orchestrator revision", run.orchestrator_revision),
            ("Orchestrator content digest", run.orchestrator_digest),
            ("Orchestrator dirty checkout", run.orchestrator_dirty),
            ("Runtime-config digest", run.runtime_config_digest),
            ("Requested baseline commit", run.baseline_ref),
            ("Baseline commit", run.baseline_commit_sha),
            ("Baseline checkpoint", run.baseline_checkpoint_id),
            ("Baseline collected tests", run.baseline_tests_collected),
            ("Baseline passing tests", run.baseline_tests_passed),
            ("Baseline skipped tests (includes expected failures)", run.baseline_tests_skipped),
            ("Requested commit", run.baseline_ref),
            ("Installed project extras", (", ".join(run.test_extras) or "None")
             if "test_extras" in run.model_fields_set else None),
            ("Baseline test-contract digest", run.baseline_test_contract_digest),
            ("Stored winner ID", run.winner_id),
            (
                "Stored patch SHA-256",
                hashlib.sha256(run.patch.encode()).hexdigest() if run.patch else None,
            ),
        ]
    )
    lines += [
        "## Recorded selection",
        "",
        "Selection order: patch-applicable candidates; prefer the recorded passed-candidate "
        "pool; then higher test pass ratio, dependency consistency, fewer lint findings, "
        "fewer changed lines, shorter elapsed time, and strategy ID.",
        "",
    ] + comparison
    lines += ["## Candidate evidence", ""]
    if not run.branches:
        lines += [
            "No candidate result is recorded. No test, timing or usage values are inferred.",
            "",
        ]
    for branch in run.branches:
        lines += [f"### {_text(branch.strategy_id)}", ""] + _table(
            [
                ("Status", branch.status),
                ("Tests collected", branch.tests_collected),
                ("Tests passed", branch.tests_passed),
                ("Tests failed / collection errors", branch.tests_failed),
                ("Tests skipped (includes expected failures)", branch.tests_skipped),
                ("Original individual test outcomes preserved", branch.test_outcomes_preserved),
                ("Dependency consistency", branch.pip_check_passed),
                ("Lint findings", branch.lint_findings),
                ("Changed files", branch.changed_files),
                ("Changed lines", branch.changed_lines),
                ("Elapsed seconds", branch.elapsed_seconds),
                ("Patch applicable", _recorded(branch, "patch_applicable")),
                ("Pydantic major", branch.pydantic_major),
                ("Test exit code", branch.test_exit_code),
                ("Dependency exit code", branch.pip_exit_code),
                ("Test contract preserved", branch.test_contract_preserved),
                ("Child checkpoint", branch.checkpoint_id),
                ("Failure reason", branch.failure_reason),
                ("Diagnostics", branch.diagnostics),
            ]
        )
    missing = [s.id for s in run.strategies if not any(b.strategy_id == s.id for b in run.branches)]
    if missing:
        lines += [
            "Planned candidates without recorded results: " + ", ".join(map(_text, missing)),
            "",
        ]
    lines += [
        "## Clean-baseline revalidation",
        "",
        "Matching clean-revalidation evidence is recorded."
        if clean
        else "Clean-baseline revalidation did not pass; its retained evidence follows."
        if revalidation is not None and revalidation.status is not BranchStatus.PASSED
        else "Clean-revalidation evidence is absent, incomplete or inconsistent.",
        "",
    ]
    lines += _table(
        [
            ("Revalidation checkpoint ID", run.revalidated_checkpoint_id),
            ("Candidate checked", revalidation.strategy_id if revalidation else None),
            ("Status", revalidation.status if revalidation else None),
            ("Tests collected", revalidation.tests_collected if revalidation else None),
            ("Tests passed", revalidation.tests_passed if revalidation else None),
            ("Tests failed", revalidation.tests_failed if revalidation else None),
            ("Tests skipped", revalidation.tests_skipped if revalidation else None),
            ("Original individual test outcomes preserved",
             revalidation.test_outcomes_preserved if revalidation else None),
            ("Pydantic major", revalidation.pydantic_major if revalidation else None),
            (
                "Test contract preserved",
                revalidation.test_contract_preserved if revalidation else None,
            ),
            ("Test exit code", revalidation.test_exit_code if revalidation else None),
            ("Dependency exit code", revalidation.pip_exit_code if revalidation else None),
            ("Dependency consistency", revalidation.pip_check_passed if revalidation else None),
            ("Failure reason", revalidation.failure_reason if revalidation else None),
            ("Diagnostics", revalidation.diagnostics if revalidation else None),
        ]
    )
    lines += _probe_review(run)
    lines += ["## Retained citations", ""]
    for citation in run.citations:
        lines += [
            f"- {_text(citation.title)} — {_text(citation.url)}",
            f"  {_text(citation.evidence)}",
        ]
    if not run.citations:
        lines.append("No citations recorded.")
    lines += [""] + _usage(run) + ["## Recorded event history", ""]
    if not events:
        lines += ["No events supplied with this export.", ""]
    for event in events:
        lines += [f"### Event {event.id}: {_text(event.type)}", ""] + _table(
            [
                ("Time", event.created_at),
                ("Branch", event.branch_id),
                ("Message", event.message),
            ]
        )
        if event.payload:
            lines += [
                "Recorded payload (escaped data):",
                "",
                _text(json.dumps(event.payload, sort_keys=True, ensure_ascii=True)),
                "",
            ]
    return "\n".join(lines).rstrip() + "\n"
