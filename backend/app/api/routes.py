from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.config import get_settings
from app.models.domain import DocumentRecord
from app.schemas.api import (
    AskRequest,
    AskResponse,
    DocumentUploadResponse,
    HealthResponse,
    ReportRequest,
)
from app.services.document_store import get_document, get_document_pdf, store_document
from app.services.pdf_service import (
    InvalidPdfError,
    PdfPageNotFoundError,
    extract_pdf_pages,
    render_pdf_page,
)
from app.services.qa_service import answer_question
from app.services.report_service import generate_report

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=get_settings().app_name)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"PDF exceeds the {limit_mb:g} MB upload limit.",
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Upload a valid PDF file.")

    try:
        pages = extract_pdf_pages(content)
    except InvalidPdfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not any(page.text.strip() for page in pages):
        raise HTTPException(status_code=422, detail="No extractable text was found in this PDF.")

    document = DocumentRecord.from_pages(file.filename or "document.pdf", pages)
    store_document(document, content)
    return DocumentUploadResponse(
        document_id=document.document_id,
        filename=document.filename,
        page_count=len(pages),
        chunk_count=len(document.chunks),
    )


@router.post("/questions/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    document_ids = list(dict.fromkeys([request.document_id, *request.additional_document_ids]))
    documents = [get_document(document_id) for document_id in document_ids]
    if any(document is None for document in documents):
        raise HTTPException(status_code=404, detail="Document not found. Upload it again to continue.")
    return answer_question(
        [document for document in documents if document is not None],
        request.question,
    )


@router.post("/reports")
def download_report(request: ReportRequest) -> Response:
    pdf_bytes = generate_report(request.question, request.result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="prooflens-report.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/pages/{page_number}")
def get_document_page(document_id: str, page_number: int) -> Response:
    pdf_bytes = get_document_pdf(document_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Document not found or no longer available.")
    try:
        page_image = render_pdf_page(pdf_bytes, page_number)
    except PdfPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidPdfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content=page_image,
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )