import CitationAction from './CitationAction'
import type { Conflict, Citation } from '../types/api'

interface ConflictComparisonProps {
  conflicts: Conflict[]
  onOpenCitation: (citation: Citation) => void
}

const datePattern = /\b(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*,?\s*\d{0,4}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)/i

export default function ConflictComparison({ conflicts, onOpenCitation }: ConflictComparisonProps) {
  return (
    <div className="conflict-comparisons">
      {conflicts.map((conflict, conflictIndex) => (
        <article className="conflict-summary" key={`${conflictIndex}-${conflict.description}`}>
          <header className="conflict-summary-header">
            <span className="conflict-chip"><i /> CONFLICT DETECTED</span>
            <p>{conflict.description}</p>
          </header>
          <div className="conflict-grid">
            {conflict.evidence.map((citation, sourceIndex) => {
              const value = datePattern.exec(citation.excerpt)?.[0]
              return (
                <section className="conflict-source" key={`${citation.document_id}-${citation.page_number}-${sourceIndex}`}>
                  <div className="conflict-source-heading">
                    <span className="conflict-source-index">SOURCE {String(sourceIndex + 1).padStart(2, '0')}</span>
                    <CitationAction citation={citation} onOpen={onOpenCitation} />
                  </div>
                  {value && <p className="conflict-value">{value}</p>}
                  <blockquote>{citation.excerpt}</blockquote>
                </section>
              )
            })}
          </div>
          <p className="conflict-caveat">ProofLens identifies the disagreement but cannot determine which source is correct.</p>
        </article>
      ))}
    </div>
  )
}