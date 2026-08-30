import type { BranchResult } from '../lib/api'

interface EvidenceTableProps {
  branches: BranchResult[]
  winnerId: string | null
}

export default function EvidenceTable({ branches, winnerId }: EvidenceTableProps) {
  if (!branches.length) {
    return <p className="empty-state">Metrics appear as each isolated branch reaches its test gate.</p>
  }
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Deterministic branch evidence comparison</caption>
        <thead>
          <tr><th>Branch</th><th>Tests</th><th>pip</th><th>Lint</th><th>Files</th><th>Lines</th></tr>
        </thead>
        <tbody>
          {branches.map((branch) => (
            <tr key={branch.strategy_id} className={branch.strategy_id === winnerId ? 'winner-row' : ''}>
              <th scope="row">{branch.strategy_id}{branch.strategy_id === winnerId ? ' ★' : ''}</th>
              <td>{branch.tests_passed}/{branch.tests_collected}</td>
              <td>{branch.pip_check_passed ? 'pass' : 'fail'}</td>
              <td>{branch.lint_findings}</td>
              <td>{branch.changed_files}</td>
              <td>{branch.changed_lines}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

