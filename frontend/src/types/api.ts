export interface UploadedDocument {
  document_id: string
  filename: string
  page_count: number
  chunk_count: number
}

export interface Evidence {
  document_id: string
  filename: string
  excerpt: string
  page_number: number
  retrieval_score: number
  status: 'retrieved'
}

export interface Citation {
  document_id: string
  filename: string
  page_number: number
  excerpt: string
}

export interface ClaimVerification {
  claim: string
  status: 'supported' | 'unsupported'
  explanation: string
  citations: Citation[]
}

export interface Conflict {
  description: string
  evidence: Citation[]
}

export interface AnswerResult {
  answer: string
  sufficient_evidence: boolean
  verification_status: 'not_verified' | 'supported' | 'unresolved' | 'contradicted' | 'insufficient_evidence'
  verification_note: string
  evidence: Evidence[]
  claims: ClaimVerification[]
  conflicts: Conflict[]
}