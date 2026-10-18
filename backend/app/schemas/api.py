from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunk_count: int


class AskRequest(BaseModel):
    document_id: str
    additional_document_ids: list[str] = Field(default_factory=list, max_length=4)
    question: str = Field(min_length=3, max_length=1000)


class CitationResponse(BaseModel):
    document_id: str
    filename: str
    page_number: int
    excerpt: str


class EvidenceResponse(CitationResponse):
    retrieval_score: float
    status: Literal["retrieved"]


class ClaimVerificationResponse(BaseModel):
    claim: str
    status: Literal["supported", "unsupported"]
    explanation: str
    citations: list[CitationResponse]


class ConflictResponse(BaseModel):
    description: str
    evidence: list[CitationResponse]


class AskResponse(BaseModel):
    answer: str
    sufficient_evidence: bool
    verification_status: Literal[
        "not_verified",
        "supported",
        "unresolved",
        "contradicted",
        "insufficient_evidence",
    ]
    verification_note: str
    evidence: list[EvidenceResponse]
    claims: list[ClaimVerificationResponse]
    conflicts: list[ConflictResponse]


class ReportRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    result: AskResponse