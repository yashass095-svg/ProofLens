import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import CitationAction from '../components/CitationAction'
import CitationViewer from '../components/CitationViewer'
import ConflictComparison from '../components/ConflictComparison'
import EvidenceList from '../components/EvidenceList'
import IntroOverlay from '../components/IntroOverlay'
import { askQuestion, downloadReport, uploadPdf } from '../services/api'
import type { AnswerResult, Citation, UploadedDocument } from '../types/api'

export default function AssistantPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    try {
      return window.localStorage.getItem('prooflens-theme') === 'light' ? 'light' : 'dark'
    } catch {
      return 'dark'
    }
  })
  const [showIntro, setShowIntro] = useState(() => {
    try {
      return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
        && window.localStorage.getItem('prooflens-intro-seen') !== 'true'
    } catch {
      return false
    }
  })
  const [documents, setDocuments] = useState<UploadedDocument[]>([])
  const [question, setQuestion] = useState('')
  const [answeredQuestion, setAnsweredQuestion] = useState('')
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const [busy, setBusy] = useState(false)
  const [reportBusy, setReportBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [notice, setNotice] = useState('')
  const [removingDocumentId, setRemovingDocumentId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const primaryDocument = documents[0]

  useEffect(() => {
    try {
      window.localStorage.setItem('prooflens-theme', theme)
    } catch {
      // The theme remains usable for this session if browser storage is unavailable.
    }
  }, [theme])

  function finishIntro() {
    try {
      window.localStorage.setItem('prooflens-intro-seen', 'true')
    } catch {
      // The intro remains skippable if browser storage is unavailable.
    }
    setShowIntro(false)
  }

  async function uploadFiles(files: File[]) {
    if (files.length === 0) return
    setBusy(true)
    setBusyMessage('Preparing document upload…')
    setError('')
    setNotice('')
    setResult(null)
    setAnsweredQuestion('')
    setSelectedCitation(null)
    const availableSlots = Math.max(0, 5 - documents.length)
    const filesToUpload = files.slice(0, availableSlots)
    const uploaded: UploadedDocument[] = []
    try {
      if (filesToUpload.length === 0) {
        throw new Error('You can compare up to five PDFs at a time.')
      }
      for (const [index, file] of filesToUpload.entries()) {
        setBusyMessage(`Processing ${file.name} · ${index + 1} of ${filesToUpload.length}`)
        uploaded.push(await uploadPdf(file))
      }
      setDocuments((current) => [...current, ...uploaded])
      setNotice(`${uploaded.length} PDF${uploaded.length === 1 ? '' : 's'} added to this workspace.`)
      if (files.length > filesToUpload.length) {
        setError('Only five PDFs can be compared at a time. The remaining files were not uploaded.')
      }
    } catch (cause) {
      if (uploaded.length > 0) {
        setDocuments((current) => [...current, ...uploaded])
      }
      setError(cause instanceof Error ? cause.message : 'PDF upload failed.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.currentTarget.files ?? [])
    event.currentTarget.value = ''
    void uploadFiles(files)
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!primaryDocument || !question.trim()) return
    setBusy(true)
    setBusyMessage('Retrieving and checking source passages…')
    setError('')
    setNotice('')
    try {
      const submittedQuestion = question.trim()
      const answer = await askQuestion(
        primaryDocument.document_id,
        submittedQuestion,
        documents.slice(1).map((source) => source.document_id),
      )
      setAnsweredQuestion(submittedQuestion)
      setResult(answer)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The question could not be answered.')
    } finally {
      setBusy(false)
      setBusyMessage('')
    }
  }

  async function handleDownloadReport() {
    if (!result || !answeredQuestion) return
    setReportBusy(true)
    setError('')
    setNotice('')
    try {
      await downloadReport(answeredQuestion, result)
      setNotice('Your report is ready to save.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The report could not be generated.')
    } finally {
      setReportBusy(false)
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    void uploadFiles(Array.from(event.dataTransfer.files))
  }

  function removeDocument(documentId: string) {
    if (removingDocumentId) return
    setRemovingDocumentId(documentId)
    window.setTimeout(() => {
      setDocuments((current) => current.filter((item) => item.document_id !== documentId))
      setResult(null)
      setAnsweredQuestion('')
      setSelectedCitation(null)
      setRemovingDocumentId(null)
    }, 220)
  }

  return (
    <main className="app-shell" data-theme={theme}>
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="ProofLens AI home">
          <span className="wordmark-mark" aria-hidden="true"><span /></span>
          <span>prooflens<span className="wordmark-ai"> / AI</span></span>
        </a>
        <div className="topbar-actions">
          <div className="topbar-note"><span className="live-dot" /> Evidence workspace <span className="topbar-divider" /> <span className="topbar-mode">SOURCE-VERIFIED</span></div>
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            <span aria-hidden="true">{theme === 'dark' ? '☼' : '◐'}</span>
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </header>

      <div className="workspace" id="top">
        <aside className="sidebar">
          <div className="section-label">WORKSPACE <span>01</span></div>
          <div className="sidebar-current"><span className="sidebar-marker" /> Document review</div>
          <div className="sidebar-rule" />
          <div className="section-label">SOURCE FILE</div>
          <div className="source-list">
            {documents.map((source, index) => (
              <div className={`file-summary ${removingDocumentId === source.document_id ? 'is-removing' : ''}`} key={source.document_id}>
                <span className="pdf-icon">PDF</span>
                <span className="file-copy"><strong title={source.filename}>{source.filename}</strong><small>{source.page_count} pages · {index === 0 ? 'primary source' : 'comparison source'}</small></span>
                <button
                  className="remove-source"
                  onClick={() => removeDocument(source.document_id)}
                  disabled={Boolean(removingDocumentId) || busy}
                  type="button"
                  aria-label={`Remove ${source.filename}`}
                  title={`Remove ${source.filename}`}
                >×</button>
              </div>
            ))}
          </div>
          <div
            className={`upload-zone ${isDragging ? 'is-dragging' : ''} ${busy ? 'is-processing' : ''}`}
            onDragOver={(event) => { event.preventDefault(); setIsDragging(true) }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDragging(false)
            }}
            onDrop={handleDrop}
          >
            <button className="upload-tile" onClick={() => inputRef.current?.click()} type="button" disabled={busy || documents.length >= 5}>
              <span className="upload-symbol" aria-hidden="true">＋</span>
              <span><strong>{busy ? 'Processing PDF' : documents.length ? 'Add comparison PDF' : 'Add PDFs'}</strong><small>{busy ? 'Upload is in progress' : 'Drop files here or browse · 20 MB each'}</small></span>
            </button>
          </div>
          <input ref={inputRef} className="visually-hidden" type="file" accept="application/pdf,.pdf" multiple onChange={handleFileChange} />
          {busy && <div className="processing-status" role="status"><span className="processing-spinner" />{busyMessage}<small>Progress is indeterminate until this operation completes.</small></div>}
          <div className="sidebar-footnote">Documents stay in this local session and are cleared when the backend restarts.</div>
        </aside>

        <section className="main-panel" aria-label="Document question and answer">
          <div className="eyebrow"><span className="eyebrow-line" /> DOCUMENT INTELLIGENCE</div>
          <h1>Ask the document.<br /><span>See what supports it.</span></h1>
          <p className="intro">Answers come with the passages and page numbers they were drawn from. You decide what the evidence establishes.</p>

          <form className="question-form" onSubmit={handleAsk}>
            <label htmlFor="question">YOUR QUESTION</label>
            <div className="question-row">
              <input
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="e.g. What is the stated project deadline?"
                maxLength={1000}
                disabled={!primaryDocument || busy}
              />
              <button type="submit" disabled={!primaryDocument || !question.trim() || busy}>
                {busy ? 'Working…' : 'Ask'} <span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>

          {busy && busyMessage.startsWith('Retrieving') && (
            <div className="answer-loading" role="status" aria-live="polite">
              <div className="answer-loading-label"><span className="processing-spinner" />{busyMessage}</div>
              <div className="answer-loading-track" aria-hidden="true" />
              <div className="answer-skeleton" aria-hidden="true" />
              <div className="answer-skeleton short" aria-hidden="true" />
            </div>
          )}

          {error && <div className="error-banner" role="alert">{error}</div>}
          {notice && <div className="success-banner" role="status"><span aria-hidden="true">✓</span>{notice}</div>}

          {result ? (
            <section className={`result-section result-${result.verification_status}`} aria-live="polite">
              <div className="result-heading">
                <div><div className="section-label">RESPONSE</div><h2>{result.verification_status === 'contradicted' ? 'Conflict detected' : result.verification_status === 'insufficient_evidence' ? 'Insufficient evidence' : result.sufficient_evidence ? 'Evidence found' : 'Not enough evidence'}</h2></div>
                <div className="result-controls">
                  <button className="report-button" type="button" onClick={handleDownloadReport} disabled={reportBusy}>
                    {reportBusy ? 'Preparing report…' : 'Download Report'}
                  </button>
                  <span className={`status-pill ${result.verification_status === 'supported' ? 'status-supported' : result.verification_status === 'contradicted' ? 'status-empty' : result.verification_status === 'insufficient_evidence' ? 'status-empty' : 'status-caution'}`}>
                    <span className="status-dot" />{result.verification_status === 'supported' ? 'TEXT MATCHED' : result.verification_status === 'contradicted' ? 'CONFLICT DETECTED' : result.verification_status === 'insufficient_evidence' ? 'INSUFFICIENT EVIDENCE' : result.verification_status === 'unresolved' ? 'UNRESOLVED' : 'NOT VERIFIED'}
                  </span>
                </div>
              </div>
              <p className="answer-text">{result.answer}</p>
              <div className="verification-note"><span aria-hidden="true">i</span>{result.verification_note}</div>
              <div className="evidence-heading"><h3>Retrieved evidence</h3><span>{result.evidence.length} {result.evidence.length === 1 ? 'passage' : 'passages'}</span></div>
              {result.verification_status !== 'contradicted' && (
                <EvidenceList evidence={result.evidence} onOpenCitation={setSelectedCitation} />
              )}
              {result.claims.length > 0 && (
                <section className="claims-section" aria-label="Claim checks">
                  <div className="evidence-heading"><h3>Claim checks</h3><span>Verbatim source matching</span></div>
                  {result.claims.map((claim, index) => (
                    <article className="claim-item" key={`${index}-${claim.claim}`}>
                      <div className="claim-meta">
                        <span>Claim {String(index + 1).padStart(2, '0')}</span>
                        <span className={`claim-status ${claim.status}`}>{claim.status}</span>
                      </div>
                      <p>{claim.claim}</p>
                      <small>{claim.explanation}</small>
                      {claim.citations.map((citation, citationIndex) => (
                        <CitationAction
                          key={`${citation.document_id}-${citation.page_number}-${citationIndex}`}
                          citation={citation}
                          onOpen={setSelectedCitation}
                        />
                      ))}
                    </article>
                  ))}
                </section>
              )}
              {result.conflicts.length > 0 && (
                <ConflictComparison conflicts={result.conflicts} onOpenCitation={setSelectedCitation} />
              )}
            </section>
          ) : (
            <div className="empty-state">
              <div className="empty-mark" aria-hidden="true"><span /><i /></div>
              <div><strong>{documents.length ? 'Your documents are ready' : 'Start with a source document'}</strong><p>{documents.length ? 'Ask a question above to retrieve passages across the selected PDFs.' : 'Upload PDFs to search their text and inspect page-level evidence.'}</p></div>
            </div>
          )}
          <footer className="disclaimer">RETRIEVED TEXT IS NOT INDEPENDENT VERIFICATION <span>·</span> ALWAYS REVIEW THE SOURCE</footer>
        </section>
      </div>
      {selectedCitation && (
        <CitationViewer
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
      {showIntro && <IntroOverlay onExplore={finishIntro} />}
    </main>
  )
}