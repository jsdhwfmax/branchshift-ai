import { FormEvent, useState } from 'react'

interface RunFormProps {
  onSubmit: (repoUrl: string) => Promise<void>
}

const DEFAULT_REPOSITORY = 'https://github.com/jsdhwfmax/branchshift-ai'

export default function RunForm({ onSubmit }: RunFormProps) {
  const [repoUrl, setRepoUrl] = useState(DEFAULT_REPOSITORY)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      const url = new URL(repoUrl)
      const path = url.pathname.split('/').filter(Boolean)
      if (url.protocol !== 'https:' || url.hostname !== 'github.com' || path.length !== 2) {
        throw new Error('Enter a public GitHub repository root URL.')
      }
      setSubmitting(true)
      await onSubmit(repoUrl)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not start the run.')
      setSubmitting(false)
    }
  }

  return (
    <form className="run-form" onSubmit={handleSubmit} noValidate>
      <div className="field-stack">
        <label htmlFor="repo-url">Public repository</label>
        <div className="input-shell">
          <span aria-hidden="true">git/</span>
          <input
            id="repo-url"
            name="repo-url"
            type="url"
            value={repoUrl}
            onChange={(event) => setRepoUrl(event.target.value)}
            aria-describedby="repo-help repo-error"
            autoComplete="url"
          />
        </div>
        <p id="repo-help" className="field-help">
          The default repository contains our bounded Pydantic v1 fixture; live execution stays sandboxed.
        </p>
        {error && <p id="repo-error" className="field-error" role="alert">{error}</p>}
      </div>
      <div className="target-block" aria-label="Migration target">
        <span>target</span>
        <strong>Pydantic v1 → v2</strong>
      </div>
      <button className="launch-button" type="submit" disabled={submitting}>
        <span>{submitting ? 'Queuing' : 'Split run'}</span>
        <span aria-hidden="true">↗</span>
      </button>
    </form>
  )
}
