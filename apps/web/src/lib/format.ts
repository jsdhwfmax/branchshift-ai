export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '—'
  const tenths = Math.round(seconds * 10) / 10
  if (tenths < 60) return `${tenths}s`
  const wholeSeconds = Math.round(seconds)
  if (wholeSeconds >= 3600) return `${Math.floor(wholeSeconds / 3600)}h ${Math.floor(wholeSeconds % 3600 / 60)}m`
  return `${Math.floor(wholeSeconds / 60)}m ${wholeSeconds % 60}s`
}
