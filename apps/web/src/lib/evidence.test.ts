import { expect, test } from 'vitest'
import type { BranchResult, RunSummary } from './api'
import { effectiveProjectPath, selectionReason, shellQuote, verification } from './evidence'

const patch = 'diff --git a/model.py b/model.py\n--- a/model.py\n+++ b/model.py\n'
export function completedRun(): RunSummary {
  const branch: BranchResult = { strategy_id: 'refactor', status: 'passed', tests_collected: 13, tests_passed: 13,
    tests_failed: 0, pip_check_passed: true, lint_findings: 1, changed_files: 3, changed_lines: 55,
    elapsed_seconds: 13, patch_applicable: true, patch, pydantic_major: 2, test_exit_code: 0, pip_exit_code: 0,
    test_contract_preserved: true, checkpoint_id: 'candidate-checkpoint' }
  return { id: 'synthetic-verification', repo_url: 'https://github.com/jsdhwfmax/branchshift-ai', target: 'pydantic-v2',
    mode: 'live', status: 'completed', created_at: '2026-10-13T00:00:00Z', updated_at: '2026-10-13T00:01:20Z',
    strategies: [], branches: [branch, { ...branch, strategy_id: 'compatibility', checkpoint_id: 'other-checkpoint', changed_lines: 82 }],
    citations: [], winner_id: 'refactor', patch, report: null, failure_reason: null,
    baseline_tests_collected: 13, baseline_checkpoint_id: 'baseline-checkpoint', baseline_commit_sha: 'a'.repeat(40),
    baseline_test_contract_digest: 'b'.repeat(64), revalidated_checkpoint_id: 'clean-checkpoint',
    revalidation: { ...branch, checkpoint_id: 'clean-checkpoint', diagnostics: '13 passed, 25 warnings\nF401 unused import' } }
}

test('requires both a fully passing candidate and exact clean revalidation', () => {
  expect(verification(completedRun()).verified).toBe(true)
})

const damage: Array<[string, (run: RunSummary) => void]> = [
  ['missing revalidation', (r) => { r.revalidation = null }],
  ['failed clean test', (r) => { r.revalidation!.test_exit_code = 1 }],
  ['skipped candidate tests', (r) => { r.branches[0].tests_passed = 12 }],
  ['skipped clean tests', (r) => { r.revalidation!.tests_passed = 12 }],
  ['missing original tests', (r) => { r.revalidation!.tests_collected = 12; r.revalidation!.tests_passed = 12 }],
  ['different test counts', (r) => { r.revalidation!.tests_collected = 14; r.revalidation!.tests_passed = 14 }],
  ['missing baseline count', (r) => { r.baseline_tests_collected = null }],
  ['missing baseline fingerprint', (r) => { r.baseline_test_contract_digest = null }],
  ['missing baseline commit', (r) => { r.baseline_commit_sha = null }],
  ['changed test contract', (r) => { r.revalidation!.test_contract_preserved = false }],
  ['unknown test contract', (r) => { r.revalidation!.test_contract_preserved = null }],
  ['version one', (r) => { r.revalidation!.pydantic_major = 1 }],
  ['dependency failure', (r) => { r.revalidation!.pip_check_passed = false }],
  ['unknown pip exit', (r) => { r.revalidation!.pip_exit_code = null }],
  ['wrong candidate', (r) => { r.revalidation!.strategy_id = 'minimal' }],
  ['changed revalidation patch', (r) => { r.revalidation!.patch += '\nchanged' }],
  ['changed selected patch', (r) => { r.branches[0].patch += '\nchanged' }],
  ['missing patch', (r) => { r.patch = null }],
  ['mismatched line count', (r) => { r.revalidation!.changed_lines = 56 }],
  ['reused baseline state', (r) => { r.revalidation!.checkpoint_id = r.baseline_checkpoint_id; r.revalidated_checkpoint_id = r.baseline_checkpoint_id }],
  ['reused candidate state', (r) => { r.revalidation!.checkpoint_id = r.branches[0].checkpoint_id; r.revalidated_checkpoint_id = r.branches[0].checkpoint_id }],
  ['mismatched clean checkpoint', (r) => { r.revalidated_checkpoint_id = 'different-checkpoint' }],
  ['unrecorded candidate checkpoint', (r) => { r.branches[0].checkpoint_id = null }],
  ['sample replay', (r) => { r.mode = 'mock' }],
]
test.each(damage)('never claims verified for %s', (_name, mutate) => {
  const run = completedRun(); mutate(run)
  expect(verification(run).verified).toBe(false)
})

test('explains smaller patch only after tests, dependencies and lint tie', () => {
  const run = completedRun()
  expect(selectionReason(run)).toMatch(/55 lines versus 82/)
  run.branches[0].changed_lines = 90
  run.branches[0].lint_findings = 0
  expect(selectionReason(run)).toMatch(/fewer lint findings: 0 versus 1/)
  expect(selectionReason(run)).not.toContain('smaller')
})

test('uses the controlled historical default only for the exact repository', () => {
  expect(effectiveProjectPath('https://github.com/jsdhwfmax/branchshift-ai.git')).toBe('fixtures/pydantic-v1-app')
  expect(effectiveProjectPath('https://github.com/other/branchshift-ai')).toBeNull()
  expect(effectiveProjectPath('https://github.com/jsdhwfmax/branchshift-ai', 'evaluation/fixtures/config')).toBe('evaluation/fixtures/config')
  expect(shellQuote("a'b")).toBe("'a'\\''b'")
})


test('allows original skips only with matching per-test outcome evidence in both checks', () => {
  const run = completedRun()
  run.baseline_tests_passed = 12; run.baseline_tests_skipped = 1
  for (const branch of [run.branches[0], run.revalidation!]) {
    branch.tests_passed = 12; branch.tests_skipped = 1; branch.test_outcomes_preserved = true
  }
  expect(verification(run).verified).toBe(true)
  run.revalidation!.test_outcomes_preserved = false
  expect(verification(run).verified).toBe(false)
  run.revalidation!.test_outcomes_preserved = true
  run.revalidation!.tests_passed = 11; run.revalidation!.tests_skipped = 2
  expect(verification(run).verified).toBe(false)
})

test('legacy records cannot acquire skips without baseline outcome evidence', () => {
  const run = completedRun()
  run.revalidation!.tests_passed = 12; run.revalidation!.tests_skipped = 1
  run.revalidation!.test_outcomes_preserved = true
  expect(verification(run).verified).toBe(false)
})
