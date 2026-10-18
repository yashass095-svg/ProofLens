import type { AnswerResult, Citation, UploadedDocument } from '../types/api'

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json() as { detail?: string }
    return body.detail ?? 'The request could not be completed.'
  } catch {
    return 'The request could not be completed.'
  }
}

export async function uploadPdf(file: File): Promise<UploadedDocument> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/documents/upload', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<UploadedDocument>
}

export async function askQuestion(
  documentId: string,
  question: string,
  additionalDocumentIds: string[] = [],
): Promise<AnswerResult> {
  const response = await fetch('/api/questions/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: documentId,
      additional_document_ids: additionalDocumentIds,
      question,
    }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<AnswerResult>
}

export function getPageImageUrl(citation: Pick<Citation, 'document_id' | 'page_number'>): string {
  return `/api/documents/${encodeURIComponent(citation.document_id)}/pages/${citation.page_number}`
}

export async function downloadReport(question: string, result: AnswerResult): Promise<void> {
  const response = await fetch('/api/reports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, result }),
  })
  if (!response.ok) throw new Error(await readError(response))

  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'prooflens-report.pdf'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}