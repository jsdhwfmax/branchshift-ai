from app.domain.models import BranchResult, BranchStatus
from app.orchestrator.evaluator import rank_results


def result(strategy_id, *, lines, elapsed=10.0, failed=0, applicable=True):
    return BranchResult(
        strategy_id=strategy_id,
        status=BranchStatus.PASSED if failed == 0 else BranchStatus.FAILED,
        tests_collected=10,
        tests_passed=10 - failed,
        tests_failed=failed,
        pip_check_passed=True,
        lint_findings=0,
        changed_files=2,
        changed_lines=lines,
        elapsed_seconds=elapsed,
        patch_applicable=applicable,
        patch="diff",
    )


def test_smallest_fully_passing_patch_wins():
    winner, verified = rank_results(
        [result("compatibility", lines=60), result("minimal", lines=32)]
    )
    assert verified is True
    assert winner is not None and winner.strategy_id == "minimal"


def test_inapplicable_patch_is_rejected():
    winner, verified = rank_results(
        [result("minimal", lines=20, applicable=False), result("refactor", lines=80)]
    )
    assert verified is True
    assert winner is not None and winner.strategy_id == "refactor"


def test_partial_result_is_labeled_unverified():
    winner, verified = rank_results([result("minimal", lines=20, failed=1)])
    assert winner is not None
    assert verified is False

