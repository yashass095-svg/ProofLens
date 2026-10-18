from app.models.domain import DocumentRecord

_documents: dict[str, DocumentRecord] = {}
_document_pdfs: dict[str, bytes] = {}


def store_document(document: DocumentRecord, pdf_bytes: bytes | None = None) -> None:
    _documents[document.document_id] = document
    if pdf_bytes is not None:
        _document_pdfs[document.document_id] = pdf_bytes


def get_document(document_id: str) -> DocumentRecord | None:
    return _documents.get(document_id)


def get_document_pdf(document_id: str) -> bytes | None:
    return _document_pdfs.get(document_id)


def clear_documents() -> None:
    _documents.clear()
    _document_pdfs.clear()