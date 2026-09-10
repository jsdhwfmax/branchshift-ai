import { useEffect, useState } from 'react'
import { eventsUrl, getRun, type RunEvent, type RunStatus, type RunSummary } from './api'
import { EVENT_TYPES, parseRunEvent } from './events'

export function isTerminal(status: RunStatus) {
  return status === 'completed' || status === 'failed' || status === 'cancelled'
}

type StreamState = 'connecting' | 'connected' | 'reconnecting' | 'closed'

export function useRunLedger(runId: string) {
  const [run, setRun] = useState<RunSummary | null>(null)
  const [events, setEvents] = useState<RunEvent[]>([])
  const [error, setError] = useState('')
  const [stream, setStream] = useState<StreamState>('connecting')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let disposed = false
    let snapshot: RunSummary | null = null
    let source: EventSource | null = null
    let streamInterrupted = false
    let streamClosed = false
    let refreshing = false
    let refreshRequested = false
    const controller = new AbortController()
    setRun(null)
    setEvents([])
    setError('')
    setStream('connecting')

    function closeStream() {
      if (streamClosed) return
      streamClosed = true
      source?.close()
      if (!disposed) setStream('closed')
    }

    function openStream() {
      if (source || disposed) return
      source = new EventSource(eventsUrl(runId))
      source.onopen = () => {
        if (disposed || streamClosed) return
        streamInterrupted = false
        setStream('connected')
        void refresh()
      }
      const listener = (raw: Event) => {
        if (disposed || streamClosed) return
        const event = parseRunEvent(raw as MessageEvent<string>)
        if (!event || event.run_id !== runId) return
        setEvents((current) => current.some((item) => item.id === event.id)
          ? current : [...current, event].sort((a, b) => a.id - b.id))
        if (event.type === 'run.completed' || event.type === 'run.failed' || event.type === 'run.cancelled') {
          closeStream()
        }
        void refresh()
      }
      EVENT_TYPES.forEach((type) => source?.addEventListener(type, listener))
      source.onerror = () => {
        if (disposed || streamClosed) return
        streamInterrupted = true
        if (snapshot && isTerminal(snapshot.status)) closeStream()
        else {
          // Keep this EventSource alive so its native Last-Event-ID cursor survives reconnects.
          setStream('reconnecting')
          void refresh()
        }
      }
    }

    async function refresh() {
      if (disposed) return
      refreshRequested = true
      if (refreshing) return
      refreshing = true
      // Coalesce bursts of SSE events, and prevent older HTTP responses replacing newer state.
      while (refreshRequested && !disposed) {
        refreshRequested = false
        try {
          const next = await getRun(runId, controller.signal)
          if (disposed) break
          snapshot = next
          setRun(next)
          setError('')
          if (streamInterrupted && isTerminal(next.status)) closeStream()
          // Completed runs still open once to replay their retained event history.
          openStream()
        } catch (caught) {
          if (!disposed) setError(caught instanceof Error ? caught.message : 'Could not load this run.')
        }
      }
      refreshing = false
    }

    void refresh()
    const poll = window.setInterval(() => {
      if (snapshot && !isTerminal(snapshot.status)) void refresh()
    }, 5000)
    return () => {
      disposed = true
      controller.abort()
      window.clearInterval(poll)
      source?.close()
    }
  }, [runId, attempt])

  return { run, events, error, stream, retry: () => setAttempt((current) => current + 1) }
}
