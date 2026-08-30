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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(body.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function createRun(repoUrl: string): Promise<RunSummary> {
  return requestJson('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl, target: 'pydantic-v2' }),
  })
}

export function getRun(runId: string): Promise<RunSummary> {
  return requestJson(`/api/runs/${runId}`)
}

export function patchUrl(runId: string): string {
  return `${API_BASE}/api/runs/${runId}/patch`
}

export function eventsUrl(runId: string): string {
  return `${API_BASE}/api/runs/${runId}/events`
}

