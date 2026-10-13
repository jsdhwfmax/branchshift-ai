interface PatchViewerProps {
  patch: string | null
  downloadUrl: string
  terminal?: boolean
  sample?: boolean
  verified?: boolean
}

export default function PatchViewer({ patch, downloadUrl, terminal = false, sample = false, verified = true }: PatchViewerProps) {
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
      {!sample && !verified && <p className="patch-disclosure">Selected candidate only. Complete clean-baseline verification is not established by the retained evidence.</p>}
      <pre tabIndex={0} aria-label={sample ? 'Sample patch contents' : verified ? 'Winning patch contents' : 'Selected candidate patch contents'}><code>{patch}</code></pre>
    </div>
  )
}
