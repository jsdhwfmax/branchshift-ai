import type { BranchResult, RunSummary } from './api'

const positiveInteger = (value: unknown): value is number => Number.isInteger(value) && Number(value) > 0
const recorded = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0

export function passedCheck(result: BranchResult | null | undefined, baselineTests: number, baselinePassed?: number | null, baselineSkipped?: number | null) {
  if (!result || result.status !== 'passed' || result.pydantic_major !== 2
    || !positiveInteger(result.tests_collected) || result.tests_collected !== baselineTests
    || result.tests_failed !== 0 || result.test_exit_code !== 0 || result.pip_exit_code !== 0
    || result.pip_check_passed !== true || result.patch_applicable !== true
    || result.test_contract_preserved !== true || result.test_outcomes_preserved === false) return false
  if (baselinePassed != null || baselineSkipped != null) {
    return Number.isInteger(baselinePassed) && Number(baselinePassed) >= 0
      && Number.isInteger(baselineSkipped) && Number(baselineSkipped) >= 0
      && Number(baselinePassed) + Number(baselineSkipped) === baselineTests
      && result.test_outcomes_preserved === true && Number.isInteger(result.tests_skipped)
      && Number(result.tests_skipped) >= 0 && Number.isInteger(result.tests_passed)
      && result.tests_passed >= Number(baselinePassed)
      && result.tests_passed + Number(result.tests_skipped) === result.tests_collected
  }
  return result.tests_passed === result.tests_collected && (result.tests_skipped ?? 0) === 0
}

export function verification(run: RunSummary): { verified: boolean; reason: string } {
  const incomplete = (reason: string) => ({ verified: false, reason })
  if (run.mode !== 'live' || run.status !== 'completed') return incomplete('This is not a completed live migration.')
  const winner = run.branches.find((branch) => branch.strategy_id === run.winner_id)
  const clean = run.revalidation
  if (!positiveInteger(run.baseline_tests_collected) || !recorded(run.baseline_checkpoint_id)
    || !/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/i.test(run.baseline_commit_sha ?? '')
    || !/^[a-f0-9]{64}$/i.test(run.baseline_test_contract_digest ?? '')) {
    return incomplete('The retained baseline test count, commit, checkpoint or test fingerprint is incomplete.')
  }
  if (!passedCheck(winner, run.baseline_tests_collected, run.baseline_tests_passed, run.baseline_tests_skipped)) return incomplete('The selected candidate does not have a complete passing Pydantic v2 test contract.')
  if (!passedCheck(clean, run.baseline_tests_collected, run.baseline_tests_passed, run.baseline_tests_skipped)) return incomplete('A complete passing clean-baseline revalidation result is not retained.')
  if (!winner || !clean || clean.strategy_id !== run.winner_id || clean.tests_collected !== winner.tests_collected) {
    return incomplete('The clean check does not match the selected candidate and its test count.')
  }
  if (!recorded(run.patch) || winner.patch !== run.patch || clean.patch !== run.patch
    || clean.changed_files !== winner.changed_files || clean.changed_lines !== winner.changed_lines) {
    return incomplete('The selected patch and clean revalidation patch do not match exactly.')
  }
  const checkpoints = [run.baseline_checkpoint_id, winner.checkpoint_id, clean.checkpoint_id]
  if (!checkpoints.every(recorded) || new Set(checkpoints).size !== 3
    || clean.checkpoint_id !== run.revalidated_checkpoint_id) {
    return incomplete('The baseline, candidate and matching clean revalidation checkpoints must be distinct.')
  }
  return { verified: true, reason: 'The exact selected patch passed again from the clean baseline, with the original test contract preserved.' }
}

export function selectionReason(run: RunSummary) {
  const winner = run.branches.find((branch) => branch.strategy_id === run.winner_id)
  if (!winner) return 'No selected candidate was retained.'
  const others = run.branches.filter((branch) => branch.strategy_id !== winner.strategy_id
    && passedCheck(branch, run.baseline_tests_collected ?? 1, run.baseline_tests_passed, run.baseline_tests_skipped))
    .sort((a, b) => a.lint_findings - b.lint_findings || a.changed_lines - b.changed_lines
      || a.elapsed_seconds - b.elapsed_seconds || a.strategy_id.localeCompare(b.strategy_id))
  const runnerUp = others[0]
  if (!runnerUp) return `${winner.strategy_id} is the only candidate with a complete passing test and dependency result.`
  if (winner.lint_findings < runnerUp.lint_findings) return `Both ${winner.strategy_id} and ${runnerUp.strategy_id} pass the test and dependency gates. ${winner.strategy_id} has fewer lint findings: ${winner.lint_findings} versus ${runnerUp.lint_findings}.`
  if (winner.lint_findings === runnerUp.lint_findings && winner.changed_lines < runnerUp.changed_lines) return `Tests, dependencies and lint are tied with ${runnerUp.strategy_id}. ${winner.strategy_id} changes ${winner.changed_lines} lines versus ${runnerUp.changed_lines}, so the smaller patch is selected.`
  if (winner.lint_findings === runnerUp.lint_findings && winner.changed_lines === runnerUp.changed_lines) return `Tests, dependencies, lint and patch size are tied with ${runnerUp.strategy_id}; recorded execution time, then branch ID, break the tie.`
  return 'Inspect the recorded comparison and selection report for this candidate.'
}

export function effectiveProjectPath(repoUrl: string, projectPath?: string | null) {
  if (projectPath) return projectPath
  try {
    const url = new URL(repoUrl)
    if (['github.com', 'www.github.com'].includes(url.hostname.toLowerCase())
      && url.pathname.replace(/\/$/, '').replace(/\.git$/i, '').toLowerCase() === '/jsdhwfmax/branchshift-ai') return 'fixtures/pydantic-v1-app'
  } catch { /* Invalid historical metadata is not a project path. */ }
  return null
}

export const shellQuote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`
