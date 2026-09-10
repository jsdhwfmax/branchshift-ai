import { useEffect, useMemo, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import BranchLane from '../components/BranchLane'
import CitationList from '../components/CitationList'
import EvidenceTable from '../components/EvidenceTable'
import PatchViewer from '../components/PatchViewer'
import RuntimeFingerprint from '../components/RuntimeFingerprint'
import HowRunWorks from '../components/HowRunWorks'
import { patchUrl, reportUrl, type BranchResult, type RunSummary } from '../lib/api'
import { isTerminal, useRunLedger } from '../lib/useRunLedger'
import { proposalProgress } from '../lib/events'

const BRANCH_IDS = ['minimal', 'compatibility', 'refactor'] as const

function branchResult(value: unknown): BranchResult | null {
  if (!value || typeof value !== 'object') return null
  const result = value as BranchResult
  if (!BRANCH_IDS.includes(result.strategy_id)
    || !['waiting', 'running', 'passed', 'failed', 'timed_out'].includes(result.status)
    || typeof result.pip_check_passed !== 'boolean' || typeof result.patch_applicable !== 'boolean'
    || ![result.tests_collected, result.tests_passed, result.tests_failed, result.lint_findings,
      result.changed_files, result.changed_lines, result.elapsed_seconds].every((number) => Number.isFinite(number) && number >= 0)) return null
  return result
}

function heading(run: RunSummary) {
  if (run.status === 'failed') return 'Run stopped.'
  if (run.status === 'cancelled') return 'Run cancelled.'
  if (run.mode === 'mock') return run.status === 'completed' ? 'Sample replay complete.' : 'Replaying sample branches.'
  if (run.status === 'completed') return hasVerifiedWinner(run) ? 'Migration verified.' : 'Run complete.'
  if (run.status === 'queued') return 'Run queued.'
  if (run.status === 'preparing') return 'Preparing the baseline.'
  if (run.status === 'planning') return 'Planning three candidates.'
  if (run.status === 'evaluating') return 'Checking the winner.'
  return 'Branches in motion.'
}

function hasVerifiedWinner(run: RunSummary) {
  const winner = run.branches.find((result) => result.strategy_id === run.winner_id)
  return run.status === 'completed' && run.mode === 'live' && !!run.patch && winner?.status === 'passed'
    && winner.pydantic_major === 2 && winner.tests_collected > 0 && winner.tests_failed === 0
    && winner.test_exit_code === 0 && winner.pip_exit_code === 0 && winner.pip_check_passed && winner.patch_applicable
    && winner.test_contract_preserved === true
}

function repositoryName(value: string) {
  try { return new URL(value).pathname.slice(1) } catch { return value }
}

export default function RunPage() {
  const { runId = '' } = useParams()
  const { run, events, error, stream, retry } = useRunLedger(runId)
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => { if (run?.id) headingRef.current?.focus() }, [run?.id])
  const branches = useMemo(() => {
    const results = new Map<string, BranchResult>()
    // Events can arrive before the summary refresh; retain partial evidence immediately.
    for (const event of events) {
      if (event.type !== 'branch.completed') continue
      const result = branchResult(event.payload.result)
      if (result && result.strategy_id === event.branch_id) results.set(result.strategy_id, result)
    }
    for (const result of run?.branches ?? []) results.set(result.strategy_id, result)
    return BRANCH_IDS.flatMap((id) => results.has(id) ? [results.get(id)!] : [])
  }, [run?.branches, events])

  if (!run) {
    return (
      <main className="run-page"><AppHeader /><section className="loading-panel" aria-live="polite">
        <h1 id="main-content" tabIndex={-1}>{error ? 'Could not load this run.' : 'Loading run ledger…'}</h1>
        {error ? <><p role="alert">{error}</p><button className="retry-button" onClick={retry}>Retry loading</button><Link to="/" className="recovery-link">Return to preflight</Link></> : <p role="status">Retrieving saved results and events.</p>}
      </section></main>
    )
  }

  const terminal = isTerminal(run.status)
  const sample = run.mode === 'mock'
  const completed = run.status === 'completed'
  const winnerId = completed ? run.winner_id : null
  const verified = hasVerifiedWinner(run)
  const ledgerLabel = sample ? 'sample' : terminal ? 'saved' : 'live'
  const streamNote = stream === 'reconnecting' && !terminal
    ? 'Event connection interrupted. Reconnecting automatically; saved results refresh when the connection resumes.'
    : ''

  return (
    <main className="run-page">
      <AppHeader mode={run.mode} />
      <section className="run-masthead">
        <div>
          <Link to="/" className="back-link">← new run</Link>
          <div className="section-kicker"><span>{run.id.slice(0, 6)}</span> run ledger</div>
          <h1 id="main-content" ref={headingRef} tabIndex={-1}>{heading(run)}</h1>
        </div>
        <dl className="run-meta">
          <div><dt>repository</dt><dd>{repositoryName(run.repo_url)}</dd></div>
          {!sample && run.project_path && <div><dt>project dir</dt><dd>{run.project_path}</dd></div>}
          <div><dt>target</dt><dd>Pydantic v1 → v2</dd></div>
          <div><dt>state</dt><dd className={`status-${run.status}`}>{run.status}</dd></div>
          <div><dt>execution</dt><dd>{sample ? 'Deterministic sample replay' : 'Live Nebius Sandbox run'}</dd></div>
          {!sample && run.baseline_commit_sha && <div><dt>commit</dt><dd title={run.baseline_commit_sha}>{run.baseline_commit_sha.slice(0, 12)}</dd></div>}
          {!sample && run.baseline_test_contract_digest && <div><dt>test contract</dt><dd title={run.baseline_test_contract_digest}>{run.baseline_test_contract_digest.slice(0, 12)} · baseline digest</dd></div>}
          {!sample && run.model_id && <div className="meta-model"><dt>model</dt><dd>{run.model_id}</dd></div>}
        </dl>
      </section>

      <section className={`execution-notice ${sample ? 'sample-notice' : ''}`} aria-label="Execution evidence scope">
        <strong>{sample ? 'SAMPLE REPLAY' : 'LIVE EXECUTION'}</strong>
        <p>{sample
          ? 'Metrics, events, and the patch illustrate the workflow using a fixed sample. No providers were called and no repository migration was verified in this run.'
          : 'Three candidate Pydantic v1 → v2 patches run from one baseline in Nebius Sandboxes. A winner is published only after clean baseline revalidation.'}</p>
        <a className="evidence-download" href={reportUrl(run.id)} download>{sample ? 'Download sample evidence (JSON)' : 'Download live evidence (JSON)'} <span aria-hidden="true">↓</span></a>
      </section>
      {terminal && !completed && <section className="failure-notice" role="alert">
        <strong>{run.status === 'cancelled' ? 'Execution cancelled' : 'Execution stopped before verification'}</strong>
        <p>{run.failure_reason || (run.status === 'cancelled' ? 'This run was cancelled.' : 'No failure detail was retained. Review the last recorded events.')}</p>
        <p>Available branch results remain below. No winning migration is verified by this run.</p>
        <Link to="/" className="recovery-link">Return to preflight</Link>
      </section>}

      <section className="branch-board" aria-label="Three migration branches">
        <h2 className="sr-only">Migration branch progress</h2>
        <div className="board-label">
          <span>{sample ? 'sample baseline' : 'Checkpoint'}</span>
          <strong title={run.baseline_checkpoint_id ?? undefined}>{sample ? `SAMPLE/${run.id.slice(0, 6)}` : run.baseline_checkpoint_id ? `${run.baseline_checkpoint_id.slice(0, 12)}…` : 'pending'}</strong>
          {!sample && run.baseline_tests_collected && <small>{run.baseline_tests_collected} baseline tests</small>}
        </div>
        <div className="branch-spine" aria-hidden="true"><span /><span /><span /></div>
        <div className="branch-list">
          {BRANCH_IDS.map((id) => {
            const branchEvents = events.filter((event) => event.branch_id === id && event.type.startsWith('branch.'))
            const lastEvent = branchEvents.at(-1)
            const progress = branchEvents.map(proposalProgress).filter((item) => item !== null).at(-1)
            return <BranchLane
              key={id}
              id={id}
              strategy={run.strategies.find((item) => item.id === id)}
              result={branches.find((item) => item.strategy_id === id)}
              active={branchEvents.length > 0}
              finished={lastEvent?.type === 'branch.completed'}
              winner={winnerId === id && (sample || verified)}
              terminal={terminal}
              sample={sample}
              message={lastEvent?.message}
              proposalProgress={progress}
            />
          })}
        </div>
        <div className={`winner-node ${winnerId && (sample || verified) ? 'locked' : ''}`}>
          <span>{winnerId ? (sample ? 'sample selection' : verified ? 'verified winner' : 'selected candidate') : 'evidence gate'}</span>
          <strong>{winnerId ?? (terminal ? 'no winner' : 'pending')}</strong>
          <small>{winnerId ? (sample ? 'illustrative outcome' : verified ? 'Pydantic v2 · revalidated' : 'verification evidence incomplete') : terminal ? 'verification incomplete' : 'tests → pip → lint → Δ lines'}</small>
          {!sample && completed && run.revalidated_checkpoint_id && <div className="winner-checkpoint" aria-label="Clean revalidation checkpoint">
            <span>clean revalidation</span><code title={run.revalidated_checkpoint_id}>{run.revalidated_checkpoint_id.slice(0, 12)}{run.revalidated_checkpoint_id.length > 12 ? '…' : ''}</code>
          </div>}
        </div>
      </section>

      <HowRunWorks mode={run.mode} modelId={run.model_id} />

      {streamNote && <p className="stream-note" role="status">{streamNote}</p>}
      {error && <p className="stream-note" role="alert">Results could not refresh: {error} <button className="retry-button" onClick={retry}>Reload ledger</button></p>}

      <section className="run-grid">
        <article className="instrument-panel evidence-panel">
          <div className="panel-title"><span>04</span><h2>{sample ? 'Sample evidence matrix' : 'Evidence matrix'}</h2></div>
          <EvidenceTable branches={branches} winnerId={sample || verified ? winnerId : null} terminal={terminal} sample={sample} />
          {winnerId && <p className={`verdict ${sample ? 'sample-verdict' : ''}`}>{sample
            ? `The fixed sample selects ${winnerId}. These metrics demonstrate the deterministic decision rule.`
            : verified ? run.report || 'The winning patch passed clean baseline revalidation on Pydantic v2.' : 'A candidate was selected, but its retained evidence does not establish a verified Pydantic v2 migration.'}</p>}
          <RuntimeFingerprint run={run} />
        </article>
        <article className="instrument-panel event-panel">
          <div className="panel-title"><span>{ledgerLabel}</span><h2>{sample ? 'Sample event ledger' : 'Event ledger'}</h2></div>
          {sample && <p className="ledger-disclosure">Illustrative events from the replay script.</p>}
          <ol className="event-list" aria-live="polite" aria-label="Recent run events">
            {events.slice(-12).reverse().map((event) => (
              <li key={event.id}>
                <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleTimeString([], { hour12: false })}</time>
                <span className={event.branch_id ? `event-dot dot-${event.branch_id}` : 'event-dot'} />
                <p>{event.message}</p>
              </li>
            ))}
          </ol>
          {!events.length && <p className="empty-state">{stream === 'closed' ? 'No event history was retained.' : terminal ? 'Loading retained event history…' : 'Waiting for the first recorded event…'}</p>}
        </article>
        <article className="instrument-panel patch-panel">
          <div className="panel-title"><span>05</span><h2>{sample ? 'Sample patch' : 'Winning patch'}</h2></div>
          <PatchViewer patch={completed ? run.patch : null} downloadUrl={patchUrl(run.id)} terminal={terminal} sample={sample} />
        </article>
        <article className="instrument-panel source-panel">
          <div className="panel-title"><span>src</span><h2>{sample ? 'Sample source set' : 'Retained sources'}</h2></div>
          <CitationList citations={run.citations} terminal={terminal} />
        </article>
      </section>
    </main>
  )
}
