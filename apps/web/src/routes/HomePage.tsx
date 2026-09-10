import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import RunForm from '../components/RunForm'
import { createRun, getIntegrationHealth, type IntegrationHealth } from '../lib/api'

const lanes = [
  ['01', 'Minimal', 'Smallest valid patch'],
  ['02', 'Compatibility', 'Safest staged bridge'],
  ['03', 'Refactor', 'Cleanest v2 model layer'],
]

export default function HomePage() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<IntegrationHealth | null>(null)
  const [healthError, setHealthError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setHealthError('')
    void getIntegrationHealth(controller.signal).then((result) => {
      if (!controller.signal.aborted) setHealth(result)
    }).catch((error) => {
      if (!controller.signal.aborted) setHealthError(error instanceof Error ? error.message : 'Could not reach the run service.')
    })
    return () => controller.abort()
  }, [attempt])
  return (
    <main>
      <AppHeader mode={health?.mode} />
      <section className="preflight-section" aria-labelledby="preflight-heading">
        <div className="section-kicker"><span>01</span> migration preflight</div>
        <div className="preflight-heading-row">
          <h1 id="preflight-heading">One baseline.<br />Three attempts.<br /><em>Proof decides.</em></h1>
          <p>
            Compare three Pydantic v1 → v2 migration candidates. In live execution, Nemotron plans;
            isolated Nebius Sandboxes test the patches; deterministic evidence selects the winner.
          </p>
        </div>
        <div className="preflight-mode" aria-live="polite">
          {healthError ? <><p role="alert">Run service unavailable: {healthError}</p><button className="retry-button" onClick={() => setAttempt((current) => current + 1)}>Retry connection</button></>
            : !health ? <p role="status">Checking execution mode…</p>
              : <p><strong>{health.mode === 'mock' ? 'SAMPLE REPLAY' : 'LIVE EXECUTION'}</strong> · {health.mode === 'mock'
                ? 'This service uses fixed sample metrics and a sample patch. No repository is migrated.'
                : health.ready ? 'Provider access is configured. Sandbox availability is checked when the run starts.'
                  : 'Provider access needs configuration before a live run can start.'}</p>}
        </div>
        <RunForm mode={health?.mode} disabled={!health?.ready || !!healthError} onSubmit={async (repoUrl, projectPath) => {
          const run = await createRun(repoUrl, projectPath)
          navigate(`/runs/${run.id}`)
        }} />
      </section>

      <section className="split-preview" aria-labelledby="split-heading">
        <div className="section-kicker"><span>02</span> branch topology</div>
        <h2 id="split-heading" className="sr-only">Three branch execution topology</h2>
        <div className="baseline-node">
          <span>BASE</span>
          <strong>pydantic-v1</strong>
          <small>baseline tests checked first</small>
        </div>
        <div className="preview-rails" aria-hidden="true"><i /><i /><i /></div>
        <div className="preview-lanes">
          {lanes.map(([code, title, note]) => (
            <div className="preview-lane" key={code}>
              <span>{code}</span><strong>{title}</strong><small>{note}</small>
            </div>
          ))}
        </div>
        <div className="winner-gate">
          <span>VERIFY</span>
          <strong>tests → pip → lint</strong>
          <small>then patch size → time → branch ID</small>
        </div>
      </section>

      <section className="how-grid" aria-labelledby="how-heading">
        <div>
          <div className="section-kicker"><span>03</span> evidence contract</div>
          <h2 id="how-heading">Three candidates.<br />One evidence gate.</h2>
        </div>
        <ol>
          <li><span>Nemotron</span><p>Returns three structured, cited migration strategies.</p></li>
          <li><span>Nebius Sandbox</span><p>Forks one exact filesystem state into independent branches.</p></li>
          <li><span>Test gate</span><p>Reapplies and ranks patches with deterministic metrics.</p></li>
        </ol>
      </section>
    </main>
  )
}
