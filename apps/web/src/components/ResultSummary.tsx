import type { RunSummary } from '../lib/api'
import { patchUrl, reportUrl } from '../lib/api'
import { selectionReason, verification } from '../lib/evidence'
import { behaviorReviewState } from '../lib/probes'

export default function ResultSummary({ run }: { run: RunSummary }) {
  if (run.mode !== 'live' || run.status !== 'completed') return null
  const check = verification(run)
  const review = behaviorReviewState(run)
  const needsReview = review === 'different' || review === 'unsupported'
  const winner = run.branches.find((branch) => branch.strategy_id === run.winner_id)
  const clean = run.revalidation
  return <section className={`result-summary ${check.verified ? 'result-verified' : 'result-incomplete'}`} aria-labelledby="result-heading">
    <div className="result-decision">
      <div className="section-kicker">{check.verified ? 'Original tests verified' : 'Evidence incomplete'}</div>
      <h2 id="result-heading">{check.verified ? `${run.winner_id} selected.` : 'Review the selected candidate.'}</h2>
      {needsReview && <p className="behavior-review-note">{review === 'different' ? 'Requested behavior examples differ from the baseline.' : 'Requested behavior review is incomplete.'} <a href="#behavior-heading">Review the observations below ↓</a></p>}
      <p className="decision-reason">{check.verified ? selectionReason(run) : check.reason}</p>
      {check.verified && winner && <dl className="outcome-metrics">
        <div><dt>candidate tests</dt><dd>{winner.tests_passed}/{winner.tests_collected}</dd></div>
        <div><dt>changed lines</dt><dd>{winner.changed_lines}</dd></div>
        <div><dt>lint findings</dt><dd>{winner.lint_findings}</dd></div>
      </dl>}
      <div className="result-actions">
        <a href="#evidence-heading">Compare candidates ↓</a>
        <a href="#patch-heading">Inspect patch ↓</a>
        {check.verified && <a href={patchUrl(run.id)} download>{needsReview ? 'Download selected patch' : 'Download checked patch'} ↓</a>}
        <a href={`${reportUrl(run.id)}?format=markdown`} download>Readable evidence report ↓</a>
      </div>
    </div>
    <div className="revalidation-result" aria-labelledby="revalidation-heading">
      <h3 id="revalidation-heading">Clean baseline revalidation</h3>
      {check.verified && clean ? <>
        <p className="clean-test-count"><strong>{clean.tests_passed}/{clean.tests_collected}</strong> tests passed again{clean.tests_skipped != null && <span className="skipped-count"> · {clean.tests_skipped} skipped</span>}</p>
        <ul><li>Exact winning patch reapplied</li><li>Pydantic {clean.pydantic_major} installed · dependency check passed</li><li>Original test contract preserved{clean.test_outcomes_preserved === true ? ' · test outcomes preserved' : ''}</li></ul>
        <p className="remaining-findings">{clean.lint_findings} lint finding{clean.lint_findings === 1 ? '' : 's'} {clean.lint_findings === 1 ? 'remains' : 'remain'}. Test warnings, if any, are retained in diagnostics.</p>
        {clean.diagnostics && <details className="strategy-details branch-diagnostics"><summary>Clean check diagnostics</summary><pre>{clean.diagnostics}</pre></details>}
      </> : <p>{check.reason}</p>}
      {run.baseline_tests_passed != null && <p className="remaining-findings">Baseline: {run.baseline_tests_passed} passed, {run.baseline_tests_skipped ?? 'unknown'} skipped. Existing skipped tests are not counted as passes.</p>}
      <p className="test-scope">{review === 'not_requested' && <>No behavior examples were requested. </>}Scope: retained tests and dependency checks. Passing them does not confirm full v2 API adoption: models may still use the v1 compatibility API. Review the diff, remaining findings and untested behavior before applying.</p>
    </div>
  </section>
}
