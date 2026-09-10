import type { RunEvent } from './api'

export const EVENT_TYPES = [
  'run.status',
  'research.ready',
  'strategies.ready',
  'branch.started',
  'branch.progress',
  'branch.completed',
  'winner.selected',
  'run.completed',
  'run.failed',
  'run.cancelled',
] as const

export function parseRunEvent(raw: MessageEvent<string>): RunEvent | null {
  try {
    const value: unknown = JSON.parse(raw.data)
    if (!value || typeof value !== 'object') return null
    const event = value as RunEvent
    if (!Number.isInteger(event.id) || event.id < 1 || typeof event.run_id !== 'string'
      || typeof event.type !== 'string' || typeof event.message !== 'string'
      || typeof event.created_at !== 'string' || !Number.isFinite(Date.parse(event.created_at))
      || (event.branch_id !== null && typeof event.branch_id !== 'string')
      || !event.payload || typeof event.payload !== 'object' || Array.isArray(event.payload)) return null
    return event
  } catch {
    return null
  }
}

export function proposalProgress(event: RunEvent) {
  if (event.type !== 'branch.progress') return null
  const { attempt, max_attempts: maxAttempts } = event.payload
  return typeof attempt === 'number' && typeof maxAttempts === 'number'
    && Number.isSafeInteger(attempt) && Number.isSafeInteger(maxAttempts)
    && attempt > 0 && maxAttempts >= attempt
    ? { attempt, maxAttempts } : null
}
