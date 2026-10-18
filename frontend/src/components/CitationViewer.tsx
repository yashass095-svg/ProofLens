import { useEffect, useState } from 'react'
import type { Citation } from '../types/api'
import { getPageImageUrl } from '../services/api'

interface CitationViewerProps {
  citation: Citation
  onClose: () => void
}

export default function CitationViewer({ citation, onClose }: CitationViewerProps) {
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    setLoaded(false)
    setLoadError(false)
  }, [citation.document_id, citation.page_number])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="citation-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section className="citation-dialog" role="dialog" aria-modal="true" aria-labelledby="citation-title">
        <header className="citation-dialog-header">
          <div>
            <div className="section-label">SOURCE DOCUMENT</div>
            <h2 id="citation-title">{citation.filename}</h2>
            <p>Page {citation.page_number}</p>
          </div>
          <button className="citation-close" type="button" onClick={onClose} aria-label="Close source viewer" title="Close">×</button>
        </header>
        <div className="citation-page-frame">
          {!loaded && !loadError && <p className="citation-loading">Loading source page…</p>}
          {loadError ? (
            <p className="citation-load-error" role="alert">This PDF page is no longer available. The cited excerpt is still shown below.</p>
          ) : (
            <img
              className="citation-page-image"
              src={getPageImageUrl(citation)}
              alt={`${citation.filename}, page ${citation.page_number}`}
              onLoad={() => setLoaded(true)}
              onError={() => setLoadError(true)}
            />
          )}
        </div>
        <div className="citation-excerpt">
          <div className="section-label">CITED EXCERPT · PAGE {citation.page_number}</div>
          <blockquote>{citation.excerpt}</blockquote>
          <p>Excerpt shown separately; page text is not highlighted.</p>
        </div>
      </section>
    </div>
  )
}