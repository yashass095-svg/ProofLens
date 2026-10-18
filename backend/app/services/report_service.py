from datetime import datetime, timezone
from html import escape
from io import BytesIO

import pymupdf

from app.schemas.api import AskResponse, CitationResponse

_STATUS_LABELS = {
    "not_verified": "Not verified",
    "supported": "Supported by a verbatim source match",
    "unresolved": "Unresolved",
    "contradicted": "Conflict detected",
    "insufficient_evidence": "Insufficient evidence",
}


def _citation_html(citation: CitationResponse) -> str:
    return (
        '<article class="source">'
        f"<h3>{escape(citation.filename)} · Page {citation.page_number}</h3>"
        f"<blockquote>{escape(citation.excerpt)}</blockquote>"
        "</article>"
    )


def generate_report(question: str, result: AskResponse) -> bytes:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status = _STATUS_LABELS[result.verification_status]
    evidence_html = "".join(_citation_html(item) for item in result.evidence)
    claims_html = "".join(
        "<article class='claim'>"
        f"<h3>{escape(claim.status.title())}: {escape(claim.claim)}</h3>"
        f"<p>{escape(claim.explanation)}</p>"
        f"{''.join(_citation_html(citation) for citation in claim.citations)}"
        "</article>"
        for claim in result.claims
    )
    conflicts_html = "".join(
        "<article class='conflict'>"
        f"<h3>Conflicting claims</h3><p>{escape(conflict.description)}</p>"
        f"{''.join(_citation_html(citation) for citation in conflict.evidence)}"
        "</article>"
        for conflict in result.conflicts
    )
    if result.verification_status == "contradicted":
        answer = (
            "The uploaded documents disagree. The system cannot determine which "
            "source is correct."
        )
    else:
        answer = result.answer
    if not evidence_html:
        evidence_html = '<p class="muted">No supporting evidence was established.</p>'

    document_html = f"""
    <html><body>
      <h1>ProofLens AI Evidence Report</h1>
      <p class="muted">Generated {escape(generated_at)}</p>
      <h2>Question</h2><p>{escape(question)}</p>
      <h2>Overall result</h2><p class="status">{escape(status)}</p>
      <h2>Answer / explanation</h2><p>{escape(answer)}</p>
      <p class="muted">{escape(result.verification_note)}</p>
      <h2>Evidence passages</h2>{evidence_html}
      {f'<h2>Claim checks</h2>{claims_html}' if claims_html else ''}
      {f'<h2>Document disagreements</h2>{conflicts_html}' if conflicts_html else ''}
      <h2>Verification limitations</h2>
      <p>A retrieved passage or verbatim text match does not establish source authenticity,
      entailment, or factual truth. Review the cited source documents before relying on
      any claim. This report records the result currently displayed by the application.</p>
    </body></html>
    """
    css = """
    body { font-family: sans-serif; font-size: 10pt; color: #202823; line-height: 1.4; }
    h1 { color: #315d46; font-size: 22pt; margin-bottom: 4pt; }
    h2 { color: #315d46; font-size: 14pt; margin-top: 18pt; border-bottom: 1px solid #dfe3dc; }
    h3 { color: #46564b; font-size: 10pt; margin-bottom: 4pt; }
    p { margin-top: 4pt; }
    .muted { color: #69746c; font-size: 9pt; }
    .status { font-weight: bold; color: #815045; }
    .source { margin: 8pt 0 12pt 0; }
    blockquote { margin: 4pt 0 0 8pt; padding-left: 8pt; border-left: 2px solid #b8cd9e; }
    .claim, .conflict { margin-top: 8pt; }
    """

    output = BytesIO()
    writer = pymupdf.DocumentWriter(output)
    story = pymupdf.Story(html=document_html, user_css=css)
    media = pymupdf.paper_rect("a4")
    content = media + (48, 48, -48, -58)
    while True:
        device = writer.begin_page(media)
        more, _ = story.place(content)
        story.draw(device)
        writer.end_page()
        if not more:
            break
    writer.close()

    report = pymupdf.open(stream=output.getvalue(), filetype="pdf")
    page_total = report.page_count
    for index, page in enumerate(report, start=1):
        page.insert_text(
            (48, page.rect.height - 28),
            f"ProofLens AI | Page {index} of {page_total}",
            fontname="helv",
            fontsize=8,
            color=(0.40, 0.46, 0.42),
        )
    return report.tobytes()