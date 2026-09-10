import type { RunSummary } from '../lib/api'

export default function RuntimeFingerprint({ run }: { run: RunSummary }) {
  if (run.mode === 'mock' || (!run.orchestrator_revision && !run.orchestrator_digest
    && run.orchestrator_dirty == null && !run.runtime_config_digest)) return null
  return (
    <details className="runtime-fingerprint">
      <summary>Runtime fingerprint</summary>
      <dl>
        {run.orchestrator_revision && <div><dt>Orchestrator revision</dt><dd title={run.orchestrator_revision}>{run.orchestrator_revision.slice(0, 12)}</dd></div>}
        {run.orchestrator_digest && <div><dt>Source digest</dt><dd title={run.orchestrator_digest}>{run.orchestrator_digest.slice(0, 12)}</dd></div>}
        <div><dt>Source checkout</dt><dd>{run.orchestrator_dirty === true ? 'contains uncommitted changes' : run.orchestrator_dirty === false ? 'clean' : 'not recorded'}</dd></div>
        {run.runtime_config_digest && <div><dt>Runtime config digest</dt><dd title={run.runtime_config_digest}>{run.runtime_config_digest.slice(0, 12)}</dd></div>}
      </dl>
      <p>Full fingerprints are retained in the evidence download.</p>
    </details>
  )
}
