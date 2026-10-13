import { FormEvent, useRef, useState } from 'react'
import { effectiveProjectPath } from '../lib/evidence'
import { serializeRunRequest, type CreateRunOptions } from '../lib/api'
import { parseBehaviorProbes } from '../lib/probes'

interface RunFormProps {
  onSubmit: (repoUrl: string, projectPath?: string, options?: CreateRunOptions) => Promise<void>
  mode?: 'mock' | 'live'
  disabled?: boolean
}

type InvalidField = 'repository' | 'project' | 'commit' | 'extras' | 'probes' | null

const DEFAULT_REPOSITORY = 'https://github.com/jsdhwfmax/branchshift-ai'

export default function RunForm({ onSubmit, mode, disabled = false }: RunFormProps) {
  const [repoUrl, setRepoUrl] = useState(DEFAULT_REPOSITORY)
  const [projectPath, setProjectPath] = useState('')
  const [baselineRef, setBaselineRef] = useState('')
  const [testExtras, setTestExtras] = useState('test')
  const [probeText, setProbeText] = useState('')
  const [error, setError] = useState('')
  const [invalidField, setInvalidField] = useState<InvalidField>(null)
  const [submitting, setSubmitting] = useState(false)
  const repositoryRef = useRef<HTMLInputElement>(null)
  const projectRef = useRef<HTMLInputElement>(null)
  const commitRef = useRef<HTMLInputElement>(null)
  const extrasRef = useRef<HTMLInputElement>(null)
  const probesRef = useRef<HTMLTextAreaElement>(null)
  const advancedRef = useRef<HTMLDetailsElement>(null)

  function clearFieldError(field: InvalidField) {
    if (invalidField === field) { setError(''); setInvalidField(null) }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (disabled || submitting) return
    setError('')
    setInvalidField(null)
    let validating: InvalidField = 'repository'
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
      const options: CreateRunOptions = {}
      if (mode === 'live') {
        validating = 'commit'
        if (baselineRef.trim()) {
          if (!/^[a-f0-9]{40}$/i.test(baselineRef.trim())) throw new Error('Use the full 40-character hexadecimal commit SHA, or leave the pinned commit empty.')
          options.baseline_ref = baselineRef.trim().toLowerCase()
        }
        validating = 'extras'
        const extras = testExtras.trim() ? testExtras.split(',').map((extra) => extra.trim()) : []
        if (extras.length > 8 || extras.some((extra) => !/^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$/.test(extra))) throw new Error('Use up to eight comma-separated test extras (1–50 letters, digits, dots, underscores or hyphens per name), or leave empty for none.')
        if (testExtras.trim() !== 'test') options.test_extras = extras
        validating = 'probes'
        if (probeText.trim()) options.behavior_probes = parseBehaviorProbes(probeText)
      }
      serializeRunRequest(url.href, projectDirectory, options)
      validating = null
      setSubmitting(true)
      if (Object.keys(options).length) await onSubmit(url.href, projectDirectory, options)
      else await onSubmit(url.href, projectDirectory)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not start the run.')
      setInvalidField(validating)
      setSubmitting(false)
      if (validating === 'repository') repositoryRef.current?.focus()
      if (validating === 'project') projectRef.current?.focus()
      if (validating && ['commit', 'extras', 'probes'].includes(validating)) {
        if (advancedRef.current) advancedRef.current.open = true
        if (validating === 'commit') commitRef.current?.focus()
        if (validating === 'extras') extrasRef.current?.focus()
        if (validating === 'probes') probesRef.current?.focus()
      }
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
            ref={repositoryRef}
            name="repo-url"
            type="url"
            value={repoUrl}
            onChange={(event) => { setRepoUrl(event.target.value); clearFieldError('repository') }}
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
            <input id="project-path" ref={projectRef} name="project-path" type="text" value={projectPath}
              placeholder="evaluation/fixtures/config" onChange={(event) => { setProjectPath(event.target.value); clearFieldError('project') }}
              aria-describedby="project-help run-error" aria-invalid={invalidField === 'project'}
              disabled={submitting} spellCheck={false} autoComplete="off" />
          </div>
          <p id="project-help" className="field-help">Path from the repository root to the Python project. Empty input uses <code>{effectiveProjectPath(repoUrl) ?? 'the repository root'}</code>.</p>
        </div>}
        {mode === 'live' && <details className="advanced-validation" ref={advancedRef}>
          <summary>Advanced validation <span>optional</span></summary>
          <p>Pin a version or supply a few examples for behavior review. Empty behavior cases keep these extra observations off.</p>
          <label htmlFor="baseline-ref">Pinned commit <span>(optional)</span></label>
          <div className="input-shell"><input id="baseline-ref" ref={commitRef} value={baselineRef} onChange={(event) => { setBaselineRef(event.target.value); clearFieldError('commit') }}
            disabled={submitting} spellCheck={false} autoComplete="off" aria-describedby="commit-help run-error" aria-invalid={invalidField === 'commit'} placeholder="Full 40-character commit SHA" /></div>
          <p id="commit-help" className="field-help">Empty uses the repository’s default branch at execution time. The resolved commit is retained in the result.</p>
          <label htmlFor="test-extras">Test extras</label>
          <div className="input-shell"><input id="test-extras" ref={extrasRef} value={testExtras} onChange={(event) => { setTestExtras(event.target.value); clearFieldError('extras') }}
            disabled={submitting} spellCheck={false} autoComplete="off" aria-describedby="extras-help run-error" aria-invalid={invalidField === 'extras'} /></div>
          <p id="extras-help" className="field-help">Comma-separated optional dependency groups from pyproject.toml, such as test,dev. Default: test. Empty installs no extras.</p>
          <label htmlFor="behavior-probes">Behavior cases JSON <span>(optional)</span></label>
          <textarea id="behavior-probes" ref={probesRef} rows={5} value={probeText} onChange={(event) => { setProbeText(event.target.value); clearFieldError('probes') }}
            disabled={submitting} spellCheck={false} autoComplete="off" aria-describedby="probes-help run-error" aria-invalid={invalidField === 'probes'}
            placeholder={'{"cases":[{"id":"example","module":"your_module","model":"YourModel","payload":{}}]}'} />
          <p id="probes-help" className="field-help">Use your project’s importable Pydantic model and 1–12 fixed JSON object inputs. Observations compare accepted/rejected inputs and serialized JSON with the original baseline. Differences are for review; they do not change the test gate or prove full compatibility. The complete request must fit in 8 KiB.</p>
        </details>}
        {mode === 'live' && <details className="supported-projects"><summary>Supported projects and what this run does</summary><p>Use a public HTTPS GitHub repository with a Python project, a pyproject.toml manifest containing a Pydantic v1 dependency, installable test dependencies and a passing pytest baseline. Other layouts and dependency formats are not supported.</p><p>The default example is our controlled 13-test fixture. No changes are pushed to your repository. The result is a patch for review, tested only against the retained original tests.</p><p>Provider configuration does not reserve a run slot. If the service allowance is exhausted, saved results above stay available.</p></details>}
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
