export type RunStatus =
  | 'queued'
  | 'preparing'
  | 'planning'
  | 'branching'
  | 'evaluating'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type BranchStatus = 'waiting' | 'running' | 'passed' | 'failed' | 'timed_out'

export interface Strategy {
  id: 'minimal' | 'compatibility' | 'refactor'
  title: string
  rationale: string
  ordered_steps: string[]
  source_urls: string[]
}

export interface BranchResult {
  strategy_id: Strategy['id']
  status: BranchStatus
  tests_collected: number
  tests_passed: number
  tests_failed: number
  pip_check_passed: boolean
  lint_findings: number
  changed_files: number
  changed_lines: number
  elapsed_seconds: number
  patch_applicable: boolean
  failure_reason?: string | null
  diagnostics?: string | null
  pydantic_major?: number | null
  test_exit_code?: number | null
  pip_exit_code?: number | null
  test_contract_preserved?: boolean | null
  checkpoint_id?: string | null
}

export interface Citation {
  title: string
  url: string
  evidence: string
}

export interface RunSummary {
  id: string
  repo_url: string
  target: string
  mode: 'mock' | 'live'
  status: RunStatus
  created_at: string
  updated_at: string
  strategies: Strategy[]
  branches: BranchResult[]
  citations: Citation[]
  winner_id: string | null
  patch: string | null
  report: string | null
  failure_reason: string | null
  baseline_commit_sha?: string | null
  baseline_checkpoint_id?: string | null
  baseline_tests_collected?: number | null
  model_id?: string | null
  provider_usage?: Record<string, number>
  baseline_test_contract_digest?: string | null
  revalidated_checkpoint_id?: string | null
  project_path?: string | null
  orchestrator_revision?: string | null
  orchestrator_digest?: string | null
  orchestrator_dirty?: boolean | null
  runtime_config_digest?: string | null
}

export interface RunEvent {
  id: number
  run_id: string
  type: string
  message: string
  created_at: string
  branch_id: string | null
  payload: Record<string, unknown>
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export interface IntegrationHealth {
  mode: RunSummary['mode']
  ready: boolean
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Request failed' }))
    const detail: unknown = body.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean).join(' ')
        : ''
    throw new Error(message || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function createRun(repoUrl: string, projectPath?: string | null): Promise<RunSummary> {
  return requestJson('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl, target: 'pydantic-v2', project_path: projectPath?.trim() || undefined }),
  })
}

export function getRun(runId: string, signal?: AbortSignal): Promise<RunSummary> {
  return requestJson(`/api/runs/${encodeURIComponent(runId)}`, { signal })
}

export function getIntegrationHealth(signal?: AbortSignal): Promise<IntegrationHealth> {
  return requestJson('/api/health/integrations', { signal })
}

export function patchUrl(runId: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/patch`
}

export function reportUrl(runId: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/report`
}

export function eventsUrl(runId: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/events`
}
