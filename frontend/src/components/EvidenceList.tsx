import CitationAction from './CitationAction'
import type { Citation, Evidence } from '../types/api'

interface EvidenceListProps {
  evidence: Evidence[]
  onOpenCitation: (citation: Citation) => void
}

export default function EvidenceList({ evidence, onOpenCitation }: EvidenceListProps) {
  if (evidence.length === 0) {
    return <p className="empty-evidence">No passages met the retrieval threshold.</p>
  }

  return (
    <div className="evidence-list">
      {evidence.map((item, index) => (
        <article className="evidence-item" key={`${item.page_number}-${index}`}>
          <div className="evidence-meta">
            <span>Source passage {String(index + 1).padStart(2, '0')}</span>
            <CitationAction citation={item} onOpen={onOpenCitation} />
          </div>
          <blockquote>{item.excerpt}</blockquote>
        </article>
      ))}
    </div>
  )
}