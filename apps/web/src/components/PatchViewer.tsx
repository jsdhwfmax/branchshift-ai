interface PatchViewerProps {
  patch: string | null
  downloadUrl: string
  terminal?: boolean
  sample?: boolean
}

export default function PatchViewer({ patch, downloadUrl, terminal = false, sample = false }: PatchViewerProps) {
  if (!patch) {
    return <p className="empty-state">{terminal ? 'No winning patch is available for this run.' : sample ? 'The sample patch appears when replay finishes.' : 'A winning diff becomes available after clean baseline revalidation.'}</p>
  }
  return (
    <div className="patch-viewer">
      <div className="patch-toolbar">
        <span>{sample ? 'sample-winner.patch' : 'winner.patch'}</span>
        <a href={downloadUrl} download>download ↓</a>
      </div>
      {sample && <p className="patch-disclosure">Illustrative sample patch. This replay did not generate or verify a repository migration.</p>}
      <pre tabIndex={0} aria-label={sample ? 'Sample patch contents' : 'Winning patch contents'}><code>{patch}</code></pre>
    </div>
  )
}
