import type { BranchResult, Strategy } from '../lib/api'

interface BranchLaneProps {
  id: Strategy['id']
  strategy?: Strategy
  result?: BranchResult
  active: boolean
  winner: boolean
}

const FALLBACK_TITLES: Record<Strategy['id'], string> = {
  minimal: 'Surgical API swap',
  compatibility: 'Compatibility bridge',
  refactor: 'Model-layer refactor',
}

export default function BranchLane({ id, strategy, result, active, winner }: BranchLaneProps) {
  const state = result?.status ?? (active ? 'running' : 'waiting')
  return (
    <article className={`branch-lane branch-${id} state-${state} ${winner ? 'is-winner' : ''}`}>
      <div className="lane-rail" aria-hidden="true"><span /></div>
      <div className="lane-copy">
        <div className="lane-heading">
          <span className="branch-code">{id.slice(0, 3).toUpperCase()}</span>
          <span className="state-chip">{winner ? 'winner' : state.replace('_', ' ')}</span>
        </div>
        <h3>{strategy?.title ?? FALLBACK_TITLES[id]}</h3>
        <p>{strategy?.rationale ?? 'Waiting for a cited migration plan.'}</p>
      </div>
      <dl className="lane-metrics">
        <div><dt>tests</dt><dd>{result ? `${result.tests_passed}/${result.tests_collected}` : '—'}</dd></div>
        <div><dt>Δ lines</dt><dd>{result ? result.changed_lines : '—'}</dd></div>
        <div><dt>lint</dt><dd>{result ? result.lint_findings : '—'}</dd></div>
        <div><dt>time</dt><dd>{result ? `${result.elapsed_seconds}s` : '—'}</dd></div>
      </dl>
    </article>
  )
}

