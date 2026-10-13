import type { BranchResult, Strategy } from '../lib/api'
import { formatDuration } from '../lib/format'

interface BranchLaneProps {
  id: Strategy['id']
  strategy?: Strategy
  result?: BranchResult
  active: boolean
  winner: boolean
  terminal?: boolean
  finished?: boolean
  sample?: boolean
  message?: string
  proposalProgress?: { attempt: number; maxAttempts: number }
}

const FALLBACK_TITLES: Record<Strategy['id'], string> = {
  minimal: 'Surgical API swap',
  compatibility: 'Compatibility bridge',
  refactor: 'Model-layer refactor',
}

export default function BranchLane({ id, strategy, result, active, winner, terminal = false, finished = false, sample = false, message, proposalProgress }: BranchLaneProps) {
  const state = result?.status ?? (terminal ? (active ? 'not_completed' : 'not_started') : finished ? 'awaiting_evidence' : active ? 'running' : 'waiting')
  const hasTests = result && result.tests_collected > 0
  return (
    <article className={`branch-lane branch-${id} state-${state} ${winner ? 'is-winner' : ''}`}>
      <div className="lane-rail" aria-hidden="true"><span /></div>
      <div className="lane-copy">
        <div className="lane-heading">
          <span className="branch-code">{id.slice(0, 3).toUpperCase()}</span>
          <span className="state-chip">{winner ? (sample ? 'sample winner' : 'winner') : state.replaceAll('_', ' ')}</span>
        </div>
        <h3>{strategy?.title ?? FALLBACK_TITLES[id]}</h3>
        <p className="proposal-label">Proposed plan · model-authored, not an execution result</p>
        <p>{strategy?.rationale ?? (terminal ? 'No migration plan was retained for this branch.' : 'Waiting for a cited migration plan.')}</p>
        {proposalProgress && <p className="branch-progress">Proposal attempts started: {proposalProgress.attempt} (limit {proposalProgress.maxAttempts})</p>}
        {!sample && result && <dl className="branch-provenance">
          <div><dt>Child checkpoint</dt><dd title={result.checkpoint_id ?? undefined}>{result.checkpoint_id ? `${result.checkpoint_id.slice(0, 12)}${result.checkpoint_id.length > 12 ? '…' : ''}` : 'not recorded'}</dd></div>
          <div><dt>Test contract</dt><dd title={result.test_contract_preserved == null ? 'The contract check did not produce a result.' : undefined} className={result.test_contract_preserved === false ? 'contract-changed' : ''}>{result.test_contract_preserved === true ? 'preserved' : result.test_contract_preserved === false ? 'changed · ineligible' : 'unknown'}</dd></div>
        </dl>}
        {(result?.failure_reason || message) && <p className={result?.failure_reason ? 'branch-failure' : 'branch-progress'}>{result?.failure_reason || message}</p>}
        {!!strategy?.ordered_steps.length && <details className="strategy-details"><summary>Migration steps</summary><ol>{strategy.ordered_steps.map((step, index) => <li key={index}>{step}</li>)}</ol></details>}
        {!!strategy?.target_files?.length && <details className="strategy-details target-files"><summary>Planned target files</summary><ul>{strategy.target_files.map((path) => <li key={path}><code>{path}</code></li>)}</ul></details>}
        {result?.diagnostics && <details className="strategy-details branch-diagnostics"><summary>Execution diagnostics</summary><pre>{result.diagnostics}</pre></details>}
      </div>
      <dl className="lane-metrics">
        <div><dt>tests</dt><dd>{hasTests ? `${result.tests_passed}/${result.tests_collected}` : '—'}{result?.tests_skipped != null && <small className="skipped-count">{result.tests_skipped} skipped</small>}</dd></div>
        <div><dt>Δ lines</dt><dd>{result ? result.changed_lines : '—'}</dd></div>
        <div><dt>Pydantic</dt><dd>{result?.pydantic_major ? `v${result.pydantic_major}` : '—'}</dd></div>
        <div><dt>time</dt><dd>{formatDuration(result?.elapsed_seconds)}</dd></div>
      </dl>
    </article>
  )
}
