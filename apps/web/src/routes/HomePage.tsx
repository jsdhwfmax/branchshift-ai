import { useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import RunForm from '../components/RunForm'
import { createRun } from '../lib/api'

const lanes = [
  ['01', 'Minimal', 'Smallest valid patch'],
  ['02', 'Compatibility', 'Safest staged bridge'],
  ['03', 'Refactor', 'Cleanest v2 model layer'],
]

export default function HomePage() {
  const navigate = useNavigate()
  return (
    <main>
      <AppHeader />
      <section className="preflight-section" aria-labelledby="preflight-heading">
        <div className="section-kicker"><span>01</span> migration preflight</div>
        <div className="preflight-heading-row">
          <h1 id="preflight-heading">One baseline.<br />Three attempts.<br /><em>Proof decides.</em></h1>
          <p>
            BranchShift turns risky dependency upgrades into a controlled race. Nemotron plans;
            isolated Sandboxes execute; tests—not taste—select the patch.
          </p>
        </div>
        <RunForm onSubmit={async (repoUrl) => {
          const run = await createRun(repoUrl)
          navigate(`/runs/${run.id}`)
        }} />
      </section>

      <section className="split-preview" aria-labelledby="split-heading">
        <div className="section-kicker"><span>02</span> branch topology</div>
        <h2 id="split-heading" className="sr-only">Three branch execution topology</h2>
        <div className="baseline-node">
          <span>BASE</span>
          <strong>pydantic-v1</strong>
          <small>18 tests passing</small>
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
          <strong>tests → size → time</strong>
        </div>
      </section>

      <section className="how-grid" aria-labelledby="how-heading">
        <div>
          <div className="section-kicker"><span>03</span> evidence contract</div>
          <h2 id="how-heading">The model proposes.<br />The system disposes.</h2>
        </div>
        <ol>
          <li><span>Nemotron</span><p>Returns three structured, cited migration strategies.</p></li>
          <li><span>Contree</span><p>Forks one exact filesystem state into independent branches.</p></li>
          <li><span>Test gate</span><p>Reapplies and ranks patches with deterministic metrics.</p></li>
        </ol>
      </section>
    </main>
  )
}

