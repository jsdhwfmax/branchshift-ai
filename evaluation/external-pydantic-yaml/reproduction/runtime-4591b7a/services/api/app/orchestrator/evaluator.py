from __future__ import annotations

from app.domain.models import BranchResult, BranchStatus


def _fully_verified(result: BranchResult) -> bool:
    return (
        result.patch_applicable
        and result.status == BranchStatus.PASSED
        and result.tests_collected > 0
        and result.tests_failed == 0
        and result.pip_check_passed
    )


def rank_results(results: list[BranchResult]) -> tuple[BranchResult | None, bool]:
    eligible = [result for result in results if result.patch_applicable]
    if not eligible:
        return None, False

    verified = [result for result in eligible if _fully_verified(result)]
    candidates = verified or eligible
    ordered = sorted(
        candidates,
        key=lambda result: (
            -result.pass_ratio,
            not result.pip_check_passed,
            result.lint_findings,
            result.changed_lines,
            result.elapsed_seconds,
            result.strategy_id,
        ),
    )
    return ordered[0], bool(verified)


def comparison_rows(results: list[BranchResult]) -> list[dict[str, object]]:
    return [
        {
            "strategy_id": result.strategy_id,
            "status": result.status.value,
            "tests": f"{result.tests_passed}/{result.tests_collected}",
            "pip_check": result.pip_check_passed,
            "lint_findings": result.lint_findings,
            "changed_files": result.changed_files,
            "changed_lines": result.changed_lines,
            "elapsed_seconds": result.elapsed_seconds,
            "patch_applicable": result.patch_applicable,
        }
        for result in sorted(results, key=lambda item: item.strategy_id)
    ]

