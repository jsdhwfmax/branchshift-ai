import { Link } from 'react-router-dom'

export default function AppHeader({ mode = 'mock' }: { mode?: 'mock' | 'live' }) {
  return (
    <header className="app-header">
      <Link className="wordmark" to="/" aria-label="BranchShift home">
        <span className="mark" aria-hidden="true"><i /><i /><i /></span>
        <span>BranchShift</span>
      </Link>
      <div className="header-status">
        <span className={`mode-dot mode-${mode}`} aria-hidden="true" />
        {mode === 'mock' ? 'deterministic replay' : 'live providers'}
      </div>
      <a className="header-link" href="https://docs.tokenfactory.nebius.com/sandboxes/overview" target="_blank" rel="noreferrer">
        built on Nebius <span aria-hidden="true">↗</span>
      </a>
    </header>
  )
}

