from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class EvidenceChunk:
    page_number: int
    text: str


@dataclass(frozen=True)
class ScoredEvidence:
    document_id: str
    filename: str
    page_number: int
    text: str
    score: float


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    filename: str
    page_count: int
    chunks: tuple[EvidenceChunk, ...]

    @classmethod
    def from_pages(cls, filename: str, pages: list[PageText]) -> "DocumentRecord":
        chunks: list[EvidenceChunk] = []
        chunk_size = 1200
        overlap = 150
        for page in pages:
            text = page.text.strip()
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                excerpt = text[start:end].strip()
                if excerpt:
                    chunks.append(EvidenceChunk(page_number=page.page_number, text=excerpt))
                if end == len(text):
                    break
                start = end - overlap
        return cls(
            document_id=str(uuid4()),
            filename=filename,
            page_count=len(pages),
            chunks=tuple(chunks),
        )