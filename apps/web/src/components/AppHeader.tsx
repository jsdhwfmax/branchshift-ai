import { Link } from 'react-router-dom'

export default function AppHeader({ mode }: { mode?: 'mock' | 'live' }) {
  return (
    <header className="app-header">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Link className="wordmark" to="/" aria-label="BranchShift home">
        <span className="mark" aria-hidden="true"><i /><i /><i /></span>
        <span>BranchShift</span>
      </Link>
      <div className="header-status">
        <span className={`mode-dot mode-${mode}`} aria-hidden="true" />
        {mode === 'mock' ? 'sample · deterministic replay' : mode === 'live' ? 'live execution' : 'execution mode pending'}
      </div>
      <a className="header-link" href="https://docs.tokenfactory.nebius.com/sandboxes/overview" target="_blank" rel="noreferrer">
        built on Nebius <span aria-hidden="true">↗</span>
      </a>
    </header>
  )
}
