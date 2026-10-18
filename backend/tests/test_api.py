from io import BytesIO
import unicodedata

import pymupdf
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services import qa_service
from app.services.document_store import clear_documents
from app.services.pdf_service import render_pdf_page

client = TestClient(app)


def make_pdf(*page_texts: str) -> bytes:
    output = BytesIO()
    document = pymupdf.open()
    for text in page_texts or ("The project deadline is Friday, 20 June.",):
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(output)
    document.close()
    return output.getvalue()


def create_report_text(question: str, result: dict) -> tuple[str, int, str]:
    response = client.post("/api/reports", json={"question": question, "result": result})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    with pymupdf.open(stream=response.content, filetype="pdf") as report:
        text = " ".join(
            unicodedata.normalize(
                "NFKC", "\n".join(page.get_text() for page in report)
            ).split()
        )
        return text, report.page_count, response.headers["content-disposition"]


def setup_function() -> None:
    clear_documents()


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_supported_answer_has_correct_filename_page_and_verbatim_claim() -> None:
    upload = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "schedule.pdf",
                make_pdf(
                    "Final report: The project team must submit its final report before the project deadline.",
                    "The project manager's home address is not provided.",
                    "Project deadline: 30 November 2026.",
                ),
                "application/pdf",
            )
        },
    )
    assert upload.status_code == 200
    document_id = upload.json()["document_id"]

    response = client.post(
        "/api/questions/ask",
        json={"document_id": document_id, "question": "What is the project deadline?"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["sufficient_evidence"] is True
    assert result["verification_status"] == "supported"
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["status"] == "retrieved"
    assert result["evidence"][0]["filename"] == "schedule.pdf"
    assert result["evidence"][0]["page_number"] == 3
    assert "30 November 2026" in result["evidence"][0]["excerpt"]
    assert result["answer"] == "Project deadline: 30 November 2026."
    assert len(result["evidence"]) == 1
    assert result["claims"][0]["status"] == "supported"
    citation = result["claims"][0]["citations"][0]
    assert citation["document_id"] == document_id
    assert citation["filename"] == "schedule.pdf"
    assert citation["page_number"] == 3
    report_text, report_pages, disposition = create_report_text(
        "What is the project deadline?", result
    )
    assert "ProofLens AI Evidence Report" in report_text
    assert "30 November 2026" in report_text
    assert "schedule.pdf" in report_text
    assert "Page 3" in report_text
    assert report_pages >= 1
    assert "filename=\"prooflens-report.pdf\"" in disposition


def test_keyword_only_deadline_mention_does_not_support_a_date_answer() -> None:
    upload = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "report-plan.pdf",
                make_pdf(
                    "Final report: The project team must submit its final report before the project deadline."
                ),
                "application/pdf",
            )
        },
    )
    response = client.post(
        "/api/questions/ask",
        json={
            "document_id": upload.json()["document_id"],
            "question": "What is the project deadline?",
        },
    )
    result = response.json()
    assert response.status_code == 200
    assert result["verification_status"] == "insufficient_evidence"
    assert result["sufficient_evidence"] is False
    assert result["claims"] == []
    assert "date" in result["answer"].lower()


def test_home_address_marked_not_provided_returns_insufficient_evidence() -> None:
    upload = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "project-record.pdf",
                make_pdf(
                    "The project manager's home address is not provided.",
                    "The project deadline is 30 November 2026.",
                ),
                "application/pdf",
            )
        },
    )
    response = client.post(
        "/api/questions/ask",
        json={
            "document_id": upload.json()["document_id"],
            "question": "What is the project manager's home address?",
        },
    )
    result = response.json()
    assert response.status_code == 200
    assert result["verification_status"] == "insufficient_evidence"
    assert result["sufficient_evidence"] is False
    assert "not provided" in result["answer"].lower()
    assert result["evidence"] == []
    report_text, _, _ = create_report_text(
        "What is the project manager's home address?", result
    )
    assert "Insufficient evidence" in report_text
    assert "not provided" in report_text.lower()


def test_incorrect_citation_is_not_attached_to_unsupported_claim(monkeypatch) -> None:
    class UnsupportedProvider:
        def answer(self, question, evidence):
            return "The project deadline is Monday, 1 July."

    monkeypatch.setattr(qa_service, "_provider", UnsupportedProvider())
    upload = client.post(
        "/api/documents/upload",
        files={"file": ("schedule.pdf", make_pdf(), "application/pdf")},
    )
    response = client.post(
        "/api/questions/ask",
        json={"document_id": upload.json()["document_id"], "question": "When is the project deadline?"},
    )
    result = response.json()
    assert response.status_code == 200
    assert result["verification_status"] == "unresolved"
    assert "cannot provide a supported answer" in result["answer"]
    assert result["claims"][0]["status"] == "unsupported"
    assert result["claims"][0]["citations"] == []


def test_non_pdf_upload_is_rejected() -> None:
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )
    assert response.status_code == 415


def test_malformed_pdf_is_rejected_safely() -> None:
    response = client.post(
        "/api/documents/upload",
        files={"file": ("broken.pdf", b"%PDF-not-a-valid-document", "application/pdf")},
    )
    assert response.status_code == 422
    assert "could not be opened" in response.json()["detail"]


def test_unmatched_question_returns_insufficient_evidence() -> None:
    upload = client.post(
        "/api/documents/upload",
        files={"file": ("schedule.pdf", make_pdf(), "application/pdf")},
    )
    response = client.post(
        "/api/questions/ask",
        json={"document_id": upload.json()["document_id"], "question": "What is the lunar habitat material?"},
    )
    assert response.status_code == 200
    assert response.json()["sufficient_evidence"] is False
    assert response.json()["verification_status"] == "insufficient_evidence"
    assert response.json()["evidence"] == []


def test_conflicting_documents_show_both_sources_and_abstain() -> None:
    first = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "ProofLens_AI_Test_Document.pdf",
                make_pdf("Project deadline: 30 November 2026."),
                "application/pdf",
            )
        },
    ).json()
    second = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "GreenTech_Revised_Schedule.pdf",
                make_pdf("Revised project deadline: 15 December 2026."),
                "application/pdf",
            )
        },
    ).json()

    response = client.post(
        "/api/questions/ask",
        json={
            "document_id": first["document_id"],
            "additional_document_ids": [second["document_id"]],
            "question": "What is the project deadline?",
        },
    )
    result = response.json()
    assert response.status_code == 200
    assert result["verification_status"] == "contradicted"
    assert "cannot give a single answer" in result["answer"]
    assert {item["filename"] for item in result["conflicts"][0]["evidence"]} == {
        "ProofLens_AI_Test_Document.pdf",
        "GreenTech_Revised_Schedule.pdf",
    }
    assert {
        (item["filename"], item["page_number"])
        for item in result["conflicts"][0]["evidence"]
    } == {
        ("ProofLens_AI_Test_Document.pdf", 1),
        ("GreenTech_Revised_Schedule.pdf", 1),
    }
    conflict_excerpts = " ".join(
        item["excerpt"] for item in result["conflicts"][0]["evidence"]
    )
    assert "Project deadline: 30 November 2026." in conflict_excerpts
    assert "Revised project deadline: 15 December 2026." in conflict_excerpts
    assert "30 November 2026" in conflict_excerpts
    assert "15 December 2026" in conflict_excerpts
    assert "conflicting" in result["conflicts"][0]["description"]
    report_text, _, _ = create_report_text("What is the project deadline?", result)
    assert "Conflict detected" in report_text
    assert "ProofLens_AI_Test_Document.pdf" in report_text
    assert "GreenTech_Revised_Schedule.pdf" in report_text
    assert "30 November 2026" in report_text
    assert "15 December 2026" in report_text
    assert "cannot determine which source is correct" in report_text.lower()


def test_page_view_endpoint_maps_each_document_id_to_its_source() -> None:
    first_pdf = make_pdf("Source A unique page content.")
    second_pdf = make_pdf("Source B different page content.")
    first_upload = client.post(
        "/api/documents/upload",
        files={"file": ("source-a.pdf", first_pdf, "application/pdf")},
    ).json()
    second_upload = client.post(
        "/api/documents/upload",
        files={"file": ("source-b.pdf", second_pdf, "application/pdf")},
    ).json()

    first_page = client.get(
        f"/api/documents/{first_upload['document_id']}/pages/1"
    )
    second_page = client.get(
        f"/api/documents/{second_upload['document_id']}/pages/1"
    )
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.headers["content-type"] == "image/png"
    assert first_page.headers["cache-control"] == "private, no-store"
    assert first_page.content == render_pdf_page(first_pdf, 1)
    assert second_page.content == render_pdf_page(second_pdf, 1)
    assert first_page.content != second_page.content
    assert client.get(
        f"/api/documents/{first_upload['document_id']}/pages/2"
    ).status_code == 404
    assert client.get("/api/documents/unknown/pages/1").status_code == 404


def test_report_paginates_long_evidence_without_losing_its_ending() -> None:
    upload = client.post(
        "/api/documents/upload",
        files={"file": ("schedule.pdf", make_pdf("Project deadline: 30 November 2026."), "application/pdf")},
    )
    result = client.post(
        "/api/questions/ask",
        json={
            "document_id": upload.json()["document_id"],
            "question": "What is the project deadline?",
        },
    ).json()
    result["evidence"][0]["excerpt"] = (
        "Long evidence passage with continuous source detail. " * 900
        + "END_OF_LONG_EVIDENCE"
    )

    report_text, report_pages, _ = create_report_text(
        "What is the project deadline?", result
    )
    assert report_pages > 1
    assert "Long evidence passage with continuous source detail." in report_text
    assert "END_OF_LONG_EVIDENCE" in report_text


def test_upload_size_limit_is_enforced(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("large.pdf", b"%PDF-" + b"x" * 10, "application/pdf")},
        )
    finally:
        get_settings.cache_clear()
    assert response.status_code == 413