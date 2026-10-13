import { expect, test } from 'vitest'
import type { BranchResult, ProbeObservation, RunSummary } from './api'
import { behaviorReviewState, parseBehaviorProbes, probeReview } from './probes'

const entry = { id: 'numeric', module: 'app.models', model: 'User', payload: { name: 123 } }
const digest = 'c'.repeat(64)
const observation: ProbeObservation = { id: 'numeric', status: 'accepted', value: { name: '123' }, error_type: null, reason: null }
const branch = { strategy_id: 'minimal', behavior_probe_results: { suite_digest: digest, observations: [observation] }, behavior_probe_comparison: { suite_digest: digest, review_only: true, cases: [{ id: 'numeric', status: 'match', basis: 'same_observation' }] } } as BranchResult
const run: RunSummary = { id: 'probe-test', repo_url: 'https://github.com/owner/repo', target: 'pydantic-v2', status: 'completed', created_at: '', updated_at: '', strategies: [], citations: [], patch: null, report: null, failure_reason: null, mode: 'live', behavior_probes: { cases: [entry] }, baseline_probe_results: { suite_digest: digest, observations: [observation] }, winner_id: 'minimal', branches: [branch], revalidation: branch }

test('validates explicit finite typed JSON input without transforming payloads', () => {
  expect(parseBehaviorProbes(JSON.stringify({ cases: [entry] }))).toEqual({ cases: [entry] })
  expect(() => parseBehaviorProbes('{"cases":[{"id":"x","module":"app","model":"Model","payload":{"n":1e400}}]}')).toThrow('finite')
})
test.each([
  { cases: [] }, { cases: [entry, entry] }, { cases: [entry], extra: true },
  { cases: [{ ...entry, module: 'app;print(1)' }] }, { cases: [{ ...entry, model: 'a.b' }] },
  { cases: [{ ...entry, payload: [] }] }, { cases: [{ ...entry, unexpected: 'value' }] },
])('rejects unsupported probe declaration %j', (value) => { expect(() => parseBehaviorProbes(JSON.stringify(value))).toThrow() })

test('matching JSON types and key-order-independent values require retained consistent comparisons', () => {
  expect(probeReview(run, branch, 'numeric').status).toBe('match')
  const reorderedRun = { ...run, baseline_probe_results: { suite_digest: digest, observations: [{ ...observation, value: { a: 1, b: 2 } }] } }
  const reorderedBranch = { ...branch, behavior_probe_results: { suite_digest: digest, observations: [{ ...observation, value: { b: 2, a: 1 } }] } }
  expect(probeReview(reorderedRun, reorderedBranch, 'numeric').status).toBe('match')
})
test('detects a supplied input changing from acceptance to rejection', () => {
  const changed: BranchResult = { ...branch,
    behavior_probe_results: { suite_digest: digest, observations: [{ ...observation, status: 'rejected', value: null, error_type: 'ValidationError' }] },
    behavior_probe_comparison: { suite_digest: digest, review_only: true, cases: [{ id: 'numeric', status: 'different', basis: 'acceptance' }] } }
  expect(probeReview(run, changed, 'numeric').status).toBe('different')
  expect(behaviorReviewState({ ...run, branches: [changed] })).toBe('different')
})
test.each([
  { behavior_probe_results: null }, { behavior_probe_comparison: null }, { behavior_probe_error: 'Probe timed out' },
  { behavior_probe_results: { suite_digest: 'd'.repeat(64), observations: [observation] } },
  { behavior_probe_results: { suite_digest: digest, observations: [observation, observation] } },
  { behavior_probe_results: { suite_digest: digest, observations: [{ ...observation, value: { name: 123 } }] } },
  { behavior_probe_results: { suite_digest: digest, observations: [{ ...observation, status: 'unsupported', reason: 'execution_interrupted', value: null }] } },
])('missing or inconsistent evidence cannot claim match: %j', (changes) => {
  const candidate = { ...branch, ...changes } as BranchResult
  expect(probeReview(run, candidate, 'numeric').status).toBe('unsupported')
  expect(behaviorReviewState({ ...run, revalidation: candidate })).toBe('unsupported')
})
test('accepted JSON null remains a valid observation and sample evidence has no probe claims', () => {
  const nullObservation = { ...observation, value: null }
  const withNull = { ...run, baseline_probe_results: { suite_digest: digest, observations: [nullObservation] } }
  expect(probeReview(withNull, { ...branch, behavior_probe_results: { suite_digest: digest, observations: [nullObservation] } }, 'numeric').status).toBe('match')
  expect(behaviorReviewState({ ...run, mode: 'mock' })).toBe('not_requested')
  expect(behaviorReviewState({ ...run, behavior_probes: null })).toBe('not_requested')
})
