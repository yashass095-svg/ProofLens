import type { Citation } from '../types/api'

interface CitationActionProps {
  citation: Citation
  onOpen: (citation: Citation) => void
}

export default function CitationAction({ citation, onOpen }: CitationActionProps) {
  return (
    <button
      className="citation-action"
      type="button"
      onClick={() => onOpen(citation)}
      aria-label={`Open ${citation.filename}, page ${citation.page_number}`}
      title="View cited PDF page and excerpt"
    >
      <span>{citation.filename}</span>
      <span>Page {citation.page_number}</span>
      <span aria-hidden="true">↗</span>
    </button>
  )
}