import type { BehaviorProbeSuite, BranchResult, ProbeObservation, RunSummary } from './api'

const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const onlyKeys = (value: Record<string, unknown>, keys: string[]) => Object.keys(value).every((key) => keys.includes(key))

export function parseBehaviorProbes(text: string): BehaviorProbeSuite {
  let value: unknown
  try { value = JSON.parse(text) } catch { throw new Error('Behavior cases must be valid JSON: {"cases":[{"id":"example","module":"your_module","model":"YourModel","payload":{}}]}.') }
  if (!object(value) || !onlyKeys(value, ['cases']) || !Array.isArray(value.cases) || value.cases.length < 1 || value.cases.length > 12) throw new Error('Provide a cases array with 1–12 behavior cases and no extra top-level fields.')
  const seen = new Set<string>()
  for (const entry of value.cases) {
    if (!object(entry) || !onlyKeys(entry, ['id','module','model','payload'])
      || typeof entry.id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(entry.id)
      || typeof entry.module !== 'string' || entry.module.length > 200 || !/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/.test(entry.module)
      || typeof entry.model !== 'string' || !/^[A-Za-z_][A-Za-z0-9_]{0,99}$/.test(entry.model)
      || !object(entry.payload)) throw new Error('Each case needs a valid id (up to 64 characters), dotted Python module (up to 200), model class name (up to 100) and JSON object payload; no extra fields.')
    if (seen.has(entry.id)) throw new Error('Each behavior case must have a unique id.')
    seen.add(entry.id)
  }
  // JSON.parse permits 1e400 -> Infinity; the API requires finite JSON values.
  JSON.stringify(value, (_key, item: unknown) => {
    if (typeof item === 'number' && !Number.isFinite(item)) throw new Error('Behavior case numbers must be finite JSON values.')
    return item
  })
  const ascii = JSON.stringify(value).replace(/[\u007f-\uffff]/g, (char) => '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0'))
  if (ascii.length > 16384) throw new Error('Behavior declarations exceed the 16 KiB declaration limit.')
  return value as unknown as BehaviorProbeSuite
}

function uniqueObservation(observations: ProbeObservation[] | undefined, id: string) {
  const matching = observations?.filter((entry) => entry.id === id)
  return matching?.length === 1 ? matching[0] : undefined
}
function available(value: ProbeObservation | undefined) {
  if (!value || value.reason) return false
  if (value.status === 'accepted') return Object.hasOwn(value, 'value') && !value.error_type
  return value.status === 'rejected' && !!value.error_type && value.value === null
}
const stableJson = (value: unknown): string => {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']'
  if (object(value)) return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}'
  return JSON.stringify(value) ?? 'undefined'
}

export function probeReview(run: RunSummary, candidate: BranchResult | null | undefined, id: string) {
  const before = uniqueObservation(run.baseline_probe_results?.observations, id)
  const after = uniqueObservation(candidate?.behavior_probe_results?.observations, id)
  const comparison = candidate?.behavior_probe_comparison
  const matches = comparison?.cases.filter((entry) => entry.id === id)
  const recorded = matches?.length === 1 ? matches[0] : undefined
  const digest = run.baseline_probe_results?.suite_digest
  const missing = { status: 'unsupported' as const, basis: 'unavailable', before, after }
  if (run.baseline_probe_error || candidate?.behavior_probe_error || !/^[0-9a-f]{64}$/.test(digest ?? '')
    || candidate?.behavior_probe_results?.suite_digest !== digest || comparison?.suite_digest !== digest
    || comparison?.review_only !== true || !available(before) || !available(after) || !recorded) return missing
  const expected = before!.status !== after!.status ? { status: 'different', basis: 'acceptance' }
    : before!.status === 'accepted' && stableJson(before!.value) !== stableJson(after!.value) ? { status: 'different', basis: 'json_output' }
      : before!.status === 'rejected' && before!.error_type !== after!.error_type ? { status: 'different', basis: 'error_type' }
        : { status: 'match', basis: 'same_observation' }
  if (recorded.status !== expected.status || recorded.basis !== expected.basis) return missing
  return { status: recorded.status, basis: recorded.basis, before, after }
}

export function behaviorReviewState(run: RunSummary): 'not_requested' | 'match' | 'different' | 'unsupported' {
  if (run.mode !== 'live' || !run.behavior_probes?.cases.length) return 'not_requested'
  const winner = run.branches.find((branch) => branch.strategy_id === run.winner_id)
  const statuses = run.behavior_probes.cases.flatMap((entry) => [probeReview(run, winner, entry.id).status, probeReview(run, run.revalidation, entry.id).status])
  if (statuses.includes('different')) return 'different'
  return statuses.every((status) => status === 'match') ? 'match' : 'unsupported'
}
