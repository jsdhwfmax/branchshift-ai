import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import BranchLane from '../components/BranchLane'
import CitationList from '../components/CitationList'
import EvidenceTable from '../components/EvidenceTable'
import PatchViewer from '../components/PatchViewer'
import { eventsUrl, getRun, patchUrl, type RunEvent, type RunSummary } from '../lib/api'
import { EVENT_TYPES, parseRunEvent } from '../lib/events'

const BRANCH_IDS = ['minimal', 'compatibility', 'refactor'] as const

export default function RunPage() {
  const { runId = '' } = useParams()
  const [run, setRun] = useState<RunSummary | null>(null)
  const [events, setEvents] = useState<RunEvent[]>([])
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      setRun(await getRun(runId))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load this run.')
    }
  }, [runId])

  useEffect(() => {
    void refresh()
    const source = new EventSource(eventsUrl(runId))
    const listener = (raw: Event) => {
      const event = parseRunEvent(raw as MessageEvent<string>)
      if (!event) return
      setEvents((current) => current.some((item) => item.id === event.id) ? current : [...current, event])
      void refresh()
    }
    EVENT_TYPES.forEach((type) => source.addEventListener(type, listener))
    source.onerror = () => {
      if (run?.status !== 'completed') setError('Live stream reconnecting…')
    }
    return () => source.close()
  }, [refresh, run?.status, runId])

  const eventBranches = useMemo(
    () => new Set(events.filter((event) => event.branch_id).map((event) => event.branch_id)),
    [events],
  )

  if (!run) {
    return (
      <main><AppHeader /><div className="loading-panel" role="status">Loading run ledger…{error && <p>{error}</p>}</div></main>
    )
  }

  return (
    <main>
      <AppHeader mode={run.mode} />
      <section className="run-masthead">
        <div>
          <Link to="/" className="back-link">← new run</Link>
          <div className="section-kicker"><span>{run.id.slice(0, 6)}</span> run ledger</div>
          <h1>{run.status === 'completed' ? 'Migration verified.' : 'Branches in motion.'}</h1>
        </div>
        <dl className="run-meta">
          <div><dt>repository</dt><dd>{new URL(run.repo_url).pathname.slice(1)}</dd></div>
          <div><dt>target</dt><dd>Pydantic v2</dd></div>
          <div><dt>state</dt><dd className={`status-${run.status}`}>{run.status}</dd></div>
        </dl>
      </section>

      <section className="branch-board" aria-labelledby="branches-heading">
        <div className="board-label">
          <span>shared checkpoint</span><strong>BASE/{run.id.slice(0, 6)}</strong>
        </div>
        <div className="branch-spine" aria-hidden="true"><span /><span /><span /></div>
        <div className="branch-list">
          {BRANCH_IDS.map((id) => (
            <BranchLane
              key={id}
              id={id}
              strategy={run.strategies.find((item) => item.id === id)}
              result={run.branches.find((item) => item.strategy_id === id)}
              active={eventBranches.has(id)}
              winner={run.winner_id === id}
            />
          ))}
        </div>
        <div className={`winner-node ${run.winner_id ? 'locked' : ''}`}>
          <span>{run.winner_id ? 'verified winner' : 'evidence gate'}</span>
          <strong>{run.winner_id ?? 'pending'}</strong>
          <small>{run.winner_id ? 'reapplied from baseline' : 'tests → lint → Δ lines'}</small>
        </div>
      </section>

      {error && <p className="stream-note" role="status">{error}</p>}

      <section className="run-grid">
        <article className="instrument-panel evidence-panel">
          <div className="panel-title"><span>04</span><h2>Evidence matrix</h2></div>
          <EvidenceTable branches={run.branches} winnerId={run.winner_id} />
          {run.report && <p className="verdict">{run.report}</p>}
        </article>
        <article className="instrument-panel event-panel">
          <div className="panel-title"><span>live</span><h2>Event ledger</h2></div>
          <ol className="event-list" aria-live="polite">
            {events.slice(-9).reverse().map((event) => (
              <li key={event.id}>
                <time>{new Date(event.created_at).toLocaleTimeString([], { hour12: false })}</time>
                <span className={event.branch_id ? `event-dot dot-${event.branch_id}` : 'event-dot'} />
                <p>{event.message}</p>
              </li>
            ))}
            {!events.length && <li className="empty-state">Opening event stream…</li>}
          </ol>
        </article>
        <article className="instrument-panel patch-panel">
          <div className="panel-title"><span>05</span><h2>Winning patch</h2></div>
          <PatchViewer patch={run.patch} downloadUrl={patchUrl(run.id)} />
        </article>
        <article className="instrument-panel source-panel">
          <div className="panel-title"><span>src</span><h2>Retained sources</h2></div>
          <CitationList citations={run.citations} />
        </article>
      </section>
    </main>
  )
}

