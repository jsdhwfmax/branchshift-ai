import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSavedRuns, type SavedRun } from '../lib/api'
import { effectiveProjectPath } from '../lib/evidence'

export default function SavedRuns() {
  const [runs, setRuns] = useState<SavedRun[] | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    void getSavedRuns(controller.signal).then((result) => {
      if (!controller.signal.aborted) setRuns(result.runs)
    }).catch((caught) => {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : 'Saved runs could not be loaded.')
    })
    return () => controller.abort()
  }, [retry])
  return <section className="saved-runs" aria-labelledby="saved-runs-heading">
    <div className="saved-runs-heading"><h2 id="saved-runs-heading">Inspect a saved run</h2><p>Open retained results without starting another migration.</p></div>
    {error ? <p role="status">Saved runs unavailable: {error} <button className="retry-button" onClick={() => setRetry((value) => value + 1)}>Retry saved runs</button></p>
      : !runs ? <p role="status">Loading recent evidence…</p>
        : !runs.length ? <p className="empty-state">No saved runs yet. Start the controlled example below.</p>
          : <ul className="saved-run-list">{runs.map((run) => <li key={run.id}>
            <Link to={`/runs/${encodeURIComponent(run.id)}`}>
              <span className="saved-run-title">{run.mode === 'live' ? 'Saved live run' : 'Sample replay'} <code>{run.id.slice(0, 8)}</code><span aria-hidden="true">↗</span></span>
              <span className="saved-run-project">{run.repo_url.replace(/^https?:\/\/(?:www\.)?github\.com\//, '').replace(/\/$/, '')} · {effectiveProjectPath(run.repo_url, run.project_path) ?? 'repository root'}</span>
              <span className="saved-run-status">{run.status.replaceAll('_', ' ')} · <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time></span>
            </Link>
          </li>)}</ul>}
  </section>
}
