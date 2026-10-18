from io import BytesIO

import pymupdf

from app.models.domain import PageText


class InvalidPdfError(ValueError):
    pass


class PdfPageNotFoundError(ValueError):
    pass


def extract_pdf_pages(content: bytes) -> list[PageText]:
    try:
        with pymupdf.open(stream=BytesIO(content), filetype="pdf") as document:
            return [
                PageText(page_number=index + 1, text=page.get_text("text"))
                for index, page in enumerate(document)
            ]
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise InvalidPdfError("The uploaded PDF could not be opened.") from exc


def render_pdf_page(content: bytes, page_number: int) -> bytes:
    try:
        with pymupdf.open(stream=BytesIO(content), filetype="pdf") as document:
            if page_number < 1 or page_number > document.page_count:
                raise PdfPageNotFoundError("The requested PDF page does not exist.")
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            return pixmap.tobytes("png")
    except PdfPageNotFoundError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise InvalidPdfError("The stored PDF page could not be rendered.") from exc