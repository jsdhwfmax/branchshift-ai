import type { ProbeObservation, RunSummary } from '../lib/api'
import { behaviorReviewState, probeReview } from '../lib/probes'

function Observation({ label, value, error, status }: { label: string; value?: ProbeObservation; error?: string | null; status?: string }) {
  return <div className="probe-observation">
    <h4>{label}</h4>
    {status && <p className={`probe-status-${status}`}>{status} vs baseline</p>}
    {error ? <p>Unavailable: {error}</p> : !value ? <p>No observation retained.</p>
      : value.status === 'accepted' && Object.hasOwn(value, 'value') ? <><p>Accepted</p><pre aria-label={`${label} JSON output`}>{JSON.stringify(value.value, null, 2)}</pre></>
        : value.status === 'rejected' ? <p>Rejected · {value.error_type ?? 'error type unavailable'}</p>
          : <p>Unsupported · {value.reason ?? 'observation unavailable'}</p>}
  </div>
}

export default function BehaviorReview({ run }: { run: RunSummary }) {
  if (run.mode !== 'live' || !run.behavior_probes?.cases.length) return null
  const winner = run.branches.find((branch) => branch.strategy_id === run.winner_id)
  const cases = run.behavior_probes.cases.map((entry) => ({ entry,
    selected: probeReview(run, winner, entry.id), clean: probeReview(run, run.revalidation, entry.id) }))
  const count = (column: 'selected' | 'clean', status: string) => cases.filter((item) => item[column].status === status).length
  const state = behaviorReviewState(run)
  return <section className="behavior-review" aria-labelledby="behavior-heading">
    <div className="section-kicker">Fixed examples · review only</div>
    <h2 id="behavior-heading">{state === 'different' ? 'Review behavior changes' : state === 'unsupported' ? 'Behavior review incomplete' : 'Requested examples match'}</h2>
    <p>These {cases.length} supplied examples compare input acceptance and serialized JSON with the original baseline. They are separate from the test gate and do not establish full behavioral compatibility. Missing or unsupported observations cannot establish a match.</p>
    <div className="probe-counts">{(['selected', 'clean'] as const).map((column) => <p key={column}><strong>{column === 'selected' ? 'Selected candidate' : 'Clean revalidation'}</strong>{count(column, 'match')} match · {count(column, 'different')} different · {count(column, 'unsupported')} unsupported</p>)}</div>
    {cases.map(({ entry, selected, clean }) => <article className="probe-case" key={entry.id}>
      <h3>{entry.id}</h3><p>{entry.module}.{entry.model}</p>
      <details><summary>Supplied input</summary><pre>{JSON.stringify(entry.payload, null, 2)}</pre></details>
      <div className="probe-observations">
        <Observation label="Original baseline" value={selected.before} error={run.baseline_probe_error} />
        <Observation label="Selected candidate" value={selected.after} error={winner?.behavior_probe_error} status={selected.status} />
        <Observation label="Clean revalidation" value={clean.after} error={run.revalidation?.behavior_probe_error} status={clean.status} />
      </div>
    </article>)}
  </section>
}
