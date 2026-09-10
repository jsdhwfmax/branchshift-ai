import type { Citation } from '../lib/api'

export default function CitationList({ citations, terminal = false }: { citations: Citation[]; terminal?: boolean }) {
  if (!citations.length) {
    return <p className="empty-state">{terminal ? 'No research sources were retained for this run.' : 'Official sources will appear after research completes.'}</p>
  }
  return (
    <ol className="citation-list">
      {citations.map((citation, index) => (
        <li key={citation.url}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <div>
            <a href={citation.url} target="_blank" rel="noreferrer">{citation.title}</a>
            <p>{citation.evidence}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
