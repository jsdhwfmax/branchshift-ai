import type { BranchResult } from '../lib/api'
import { formatDuration } from '../lib/format'

interface EvidenceTableProps {
  branches: BranchResult[]
  winnerId: string | null
  terminal?: boolean
  sample?: boolean
}

export default function EvidenceTable({ branches, winnerId, terminal = false, sample = false }: EvidenceTableProps) {
  if (!branches.length) {
    return <p className="empty-state">{terminal ? 'No branch test results were retained. Review the failure reason and event ledger.' : 'Metrics appear as each isolated branch reaches its test gate.'}</p>
  }
  return (
    <div className="table-wrap" role="region" aria-label="Branch evidence comparison" tabIndex={0}>
      <table>
        <caption>{sample ? 'Illustrative sample metrics · no Sandbox execution' : 'Retained branch results'} · — means no recorded test evidence</caption>
        <thead>
          <tr><th>Branch</th><th>State</th>{!sample && <th>Test contract</th>}<th>Pydantic</th><th>Tests</th><th>pip</th><th>Lint</th><th>Files</th><th>Lines</th><th>Time</th><th>Patch</th></tr>
        </thead>
        <tbody>
          {branches.map((branch) => (
            <tr key={branch.strategy_id} className={branch.strategy_id === winnerId ? 'winner-row' : ''}>
              <th scope="row">{branch.strategy_id}{branch.strategy_id === winnerId ? ' ★' : ''}</th>
              <td>{branch.status.replaceAll('_', ' ')}</td>
              {!sample && <td title={branch.test_contract_preserved == null ? 'The contract check did not produce a result.' : undefined} className={branch.test_contract_preserved === false ? 'contract-changed' : ''}>{branch.test_contract_preserved === true ? 'preserved' : branch.test_contract_preserved === false ? 'changed' : 'unknown'}</td>}
              <td>{branch.pydantic_major ? `v${branch.pydantic_major}` : '—'}</td>
              <td>{branch.tests_collected ? `${branch.tests_passed}/${branch.tests_collected}` : '—'}{branch.tests_skipped != null && <small className="skipped-count">{branch.tests_skipped} skipped</small>}</td>
              <td>{branch.pip_exit_code == null ? '—' : branch.pip_exit_code === 0 && branch.pip_check_passed ? 'pass' : 'fail'}</td>
              <td>{branch.tests_collected ? branch.lint_findings : '—'}</td>
              <td>{branch.changed_files}</td>
              <td>{branch.changed_lines}</td>
              <td className="duration-value">{formatDuration(branch.elapsed_seconds)}</td>
              <td>{branch.patch_applicable ? 'applies' : 'unverified'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
