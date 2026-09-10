import { FormEvent, useState } from 'react'

interface RunFormProps {
  onSubmit: (repoUrl: string, projectPath?: string) => Promise<void>
  mode?: 'mock' | 'live'
  disabled?: boolean
}

const DEFAULT_REPOSITORY = 'https://github.com/jsdhwfmax/branchshift-ai'

export default function RunForm({ onSubmit, mode, disabled = false }: RunFormProps) {
  const [repoUrl, setRepoUrl] = useState(DEFAULT_REPOSITORY)
  const [projectPath, setProjectPath] = useState('')
  const [error, setError] = useState('')
  const [invalidField, setInvalidField] = useState<'repository' | 'project' | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (disabled || submitting) return
    setError('')
    setInvalidField(null)
    let validating: 'repository' | 'project' | null = 'repository'
    try {
      const url = new URL(repoUrl.trim())
      const path = url.pathname.split('/').filter(Boolean)
      if (url.protocol !== 'https:' || !['github.com', 'www.github.com'].includes(url.hostname) || path.length !== 2
        || url.username || url.password || url.port || url.search || url.hash) {
        throw new Error('Enter a public GitHub repository root URL.')
      }
      validating = 'project'
      const projectDirectory = mode === 'live' ? projectPath.trim() || undefined : undefined
      if (projectDirectory && (projectDirectory.length > 200
        || !/^[A-Za-z0-9._-]+(?:\/[A-Za-z0-9._-]+)*$/.test(projectDirectory)
        || projectDirectory.split('/').some((part) => part === '.' || part === '..'))) {
        throw new Error('Use a repository-relative directory of at most 200 characters: letters, digits, dots, underscores, hyphens, and forward slashes. Do not use empty, . or .. path segments.')
      }
      validating = null
      setSubmitting(true)
      await onSubmit(url.href, projectDirectory)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not start the run.')
      setInvalidField(validating)
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
            aria-describedby="repo-help run-error"
            aria-invalid={invalidField === 'repository'}
            disabled={submitting}
            spellCheck={false}
            autoComplete="url"
          />
        </div>
        <p id="repo-help" className="field-help">
          {mode === 'mock' ? 'Replay uses a fixed Pydantic fixture; this URL does not change the sample results.' : 'The default repository contains our bounded Pydantic v1 fixture; live execution stays sandboxed.'}
        </p>
        {mode === 'live' && <div className="project-directory">
          <label htmlFor="project-path">Project directory <span>(optional)</span></label>
          <div className="input-shell">
            <input id="project-path" name="project-path" type="text" value={projectPath}
              placeholder="evaluation/fixtures/config" onChange={(event) => setProjectPath(event.target.value)}
              aria-describedby="project-help run-error" aria-invalid={invalidField === 'project'}
              disabled={submitting} spellCheck={false} autoComplete="off" />
          </div>
          <p id="project-help" className="field-help">Path from the repository root to the Python project. Leave empty to keep the default project location.</p>
        </div>}
        {error && <p id="run-error" className="field-error" role="alert">{error}</p>}
      </div>
      <div className="target-block" aria-label="Migration target">
        <span>target</span>
        <strong>Pydantic v1 → v2</strong>
      </div>
      <button className="launch-button" type="submit" disabled={submitting || disabled}>
        <span>{submitting ? 'Queuing…' : mode === 'mock' ? 'Replay sample' : 'Split run'}</span>
        <span aria-hidden="true">↗</span>
      </button>
    </form>
  )
}
