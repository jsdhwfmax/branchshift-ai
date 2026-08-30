interface PatchViewerProps {
  patch: string | null
  downloadUrl: string
}

export default function PatchViewer({ patch, downloadUrl }: PatchViewerProps) {
  if (!patch) {
    return <p className="empty-state">The verified unified diff will unlock after reapplication.</p>
  }
  return (
    <div className="patch-viewer">
      <div className="patch-toolbar">
        <span>winner.patch</span>
        <a href={downloadUrl} download>download ↓</a>
      </div>
      <pre tabIndex={0}><code>{patch}</code></pre>
    </div>
  )
}

