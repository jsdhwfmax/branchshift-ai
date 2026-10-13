import type { RunSummary } from '../lib/api'
import { effectiveProjectPath, shellQuote, verification } from '../lib/evidence'

export default function ApplyPatchGuide({ run }: { run: RunSummary }) {
  if (!verification(run).verified) return null
  const project = effectiveProjectPath(run.repo_url, run.project_path)
  const directory = project ? ` --directory=${shellQuote(project)}` : ''
  const commit = run.baseline_commit_sha!
  const command = `git worktree add --detach ../branchshift-review ${shellQuote(commit)}\ncd ../branchshift-review\ngit apply${directory} --check /absolute/path/to/winner.patch\ngit apply${directory} /absolute/path/to/winner.patch`
  return <details className="apply-guide">
    <summary>Apply this patch to the recorded commit</summary>
    <p>Download the verified patch, then run these commands from an existing clone of this repository. Use a new, unused worktree directory so your current checkout stays intact. Replace the patch path with its saved absolute path.</p>
    <p>Base commit: <code>{commit}</code><br />Patch paths are relative to <code>{project ?? 'the repository root'}</code>.</p>
    <pre tabIndex={0} aria-label="Patch application commands"><code>{command}</code></pre>
    <p>If the commit is missing locally, fetch it from the repository first. Stop if the check fails. After applying, install and test using the project’s documented setup; the hosted result only covers the recorded baseline and test contract.</p>
  </details>
}
