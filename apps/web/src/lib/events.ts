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
] as const

export function parseRunEvent(raw: MessageEvent<string>): RunEvent | null {
  try {
    return JSON.parse(raw.data) as RunEvent
  } catch {
    return null
  }
}

