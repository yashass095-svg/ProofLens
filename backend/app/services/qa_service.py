import re
from itertools import combinations

from app.core.config import get_settings
from app.models.domain import DocumentRecord, ScoredEvidence
from app.schemas.api import (
    AskResponse,
    CitationResponse,
    ClaimVerificationResponse,
    ConflictResponse,
    EvidenceResponse,
)
from app.services.providers import AnswerProvider, ExtractiveAnswerProvider
from app.services.retrieval import ConfiguredRetriever

_retriever = ConfiguredRetriever()
_provider: AnswerProvider = ExtractiveAnswerProvider()
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_VALUE_PATTERN = re.compile(
    r"(?<!\w)(?:"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{1,2}(?:,?\s+\d{4})?|"
    r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)|"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
    r"\d+(?:\.\d+)?%?|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r")(?!\w)",
    re.IGNORECASE,
)
_DATE_VALUE_PATTERN = re.compile(
    r"(?<!\w)(?:"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{1,2}(?:,?\s+\d{4})?|"
    r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s*,?\s*\d{0,4}|"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r")(?!\w)",
    re.IGNORECASE,
)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "this", "to", "was", "what", "when",
    "where", "which", "with",
}
_UNAVAILABLE_PATTERN = re.compile(
    r"\b(?:"
    r"not\s+(?:provided|available|specified|disclosed|listed|included|stated|known|found|on\s+file)|"
    r"unavailable|unknown|missing|withheld|undisclosed|n/?a|"
    r"(?:does|do|did)\s+not\s+(?:provide|contain|list|state|include|specify)|"
    r"no\s+(?:record|information|details?)\s+(?:of|for|about)"
    r")\b",
    re.IGNORECASE,
)


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
        if len(token) > 1 and token.lower() not in _STOP_WORDS
    }


def _citation(item: ScoredEvidence) -> CitationResponse:
    return CitationResponse(
        document_id=item.document_id,
        filename=item.filename,
        page_number=item.page_number,
        excerpt=item.text,
    )


def _relevant_values(
    text: str, query_tokens: set[str], compare_dates: bool
) -> set[str]:
    values: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if query_tokens & _tokens(sentence):
            if compare_dates:
                values.update(
                    " ".join(value.lower().replace(",", "").split())
                    for value in _DATE_VALUE_PATTERN.findall(sentence)
                )
            else:
                values.update(value.lower() for value in _VALUE_PATTERN.findall(sentence))
    return values


def _find_conflicts(
    question: str, evidence: list[ScoredEvidence]
) -> list[ConflictResponse]:
    query_tokens = _tokens(question)
    compare_dates = _requires_date_value(question)
    for left, right in combinations(evidence, 2):
        if left.document_id == right.document_id:
            continue
        left_values = _relevant_values(left.text, query_tokens, compare_dates)
        right_values = _relevant_values(right.text, query_tokens, compare_dates)
        if left_values and right_values and left_values.isdisjoint(right_values):
            return [
                ConflictResponse(
                    description=(
                        "Retrieved passages from different documents give conflicting "
                        "date or numeric values relevant to this question. The evidence "
                        "does not establish which value is correct."
                    ),
                    evidence=[_citation(left), _citation(right)],
                )
            ]
    return []


def _normalized(text: str) -> str:
    return " ".join(token.lower() for token in _TOKEN_PATTERN.findall(text))


def _requires_date_value(question: str) -> bool:
    question_terms = {token.lower() for token in _TOKEN_PATTERN.findall(question)}
    return bool(question_terms & {"when", "date", "deadline"})


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
        if sentence.strip()
    ]


def _matching_sentences(
    question: str, evidence: list[ScoredEvidence]
) -> list[ScoredEvidence]:
    query_tokens = _tokens(question)
    minimum_overlap = max(1, (len(query_tokens) * 3 + 3) // 4)
    requires_date = _requires_date_value(question)
    excerpts: list[ScoredEvidence] = []
    seen: set[tuple[str, int, str]] = set()
    for item in evidence:
        matches = [
            (
                bool(_DATE_VALUE_PATTERN.search(sentence)),
                len(query_tokens & _tokens(sentence)),
                index,
                sentence,
            )
            for index, sentence in enumerate(_sentences(item.text))
            if len(query_tokens & _tokens(sentence)) >= minimum_overlap
            and (not requires_date or _DATE_VALUE_PATTERN.search(sentence))
        ]
        if not matches:
            continue
        _, _, _, excerpt = max(
            matches,
            key=lambda match: (
                match[0],
                match[1],
                len(_tokens(match[3])),
                -match[2],
            ),
        )
        key = (item.document_id, item.page_number, excerpt)
        if key not in seen:
            seen.add(key)
            excerpts.append(
                ScoredEvidence(
                    document_id=item.document_id,
                    filename=item.filename,
                    page_number=item.page_number,
                    text=excerpt,
                    score=item.score,
                )
            )
    return excerpts


def _unavailable_evidence(
    question: str, evidence: list[ScoredEvidence]
) -> list[ScoredEvidence]:
    query_tokens = _tokens(question)
    minimum_overlap = max(1, (len(query_tokens) * 3 + 3) // 4)
    unavailable: list[ScoredEvidence] = []
    for item in evidence:
        for sentence in _sentences(item.text):
            overlap = len(query_tokens & _tokens(sentence))
            if overlap >= minimum_overlap and _UNAVAILABLE_PATTERN.search(sentence):
                unavailable.append(
                    ScoredEvidence(
                        document_id=item.document_id,
                        filename=item.filename,
                        page_number=item.page_number,
                        text=sentence,
                        score=item.score,
                    )
                )
    return unavailable


def _verify_claims(
    answer: str, evidence: list[ScoredEvidence]
) -> list[ClaimVerificationResponse]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer)
        if sentence.strip()
    ]
    claims: list[ClaimVerificationResponse] = []
    for sentence in sentences:
        normalized_claim = _normalized(sentence)
        citations = [
            _citation(item)
            for item in evidence
            if f" {normalized_claim} " in f" {_normalized(item.text)} "
        ]
        supported = bool(citations)
        claims.append(
            ClaimVerificationResponse(
                claim=sentence,
                status="supported" if supported else "unsupported",
                explanation=(
                    "This claim appears verbatim in the cited passage."
                    if supported
                    else "No retrieved passage contains this claim verbatim."
                ),
                citations=citations,
            )
        )
    return claims


def answer_question(documents: list[DocumentRecord], question: str) -> AskResponse:
    candidates = [
        candidate
        for document in documents
        for candidate in _retriever.retrieve(document, question)
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    threshold = get_settings().retrieval_threshold
    evidence = [candidate for candidate in candidates if candidate.score >= threshold]

    if not evidence:
        return AskResponse(
            answer="I could not find enough relevant evidence in the uploaded documents to answer that question.",
            sufficient_evidence=False,
            verification_status="insufficient_evidence",
            verification_note="No passage met the retrieval threshold. This does not prove that the documents contain no answer.",
            evidence=[],
            claims=[],
            conflicts=[],
        )

    unavailable = _unavailable_evidence(question, evidence)
    if unavailable:
        return AskResponse(
            answer=(
                "Insufficient evidence: the requested information was not found. "
                "The document explicitly says it is not provided."
            ),
            sufficient_evidence=False,
            verification_status="insufficient_evidence",
            verification_note=(
                "A retrieved passage states that the requested information is unavailable; "
                "that passage is not evidence of the missing value."
            ),
            evidence=[],
            claims=[],
            conflicts=[],
        )

    relevant_evidence = _matching_sentences(question, evidence)
    if not relevant_evidence:
        answer = (
            "Insufficient evidence: no deadline date was found in the relevant passages."
            if _requires_date_value(question)
            else "Insufficient evidence: the requested information was not found in the relevant passages."
        )
        verification_note = (
            "The retrieved passages mention the deadline but do not provide a date value."
            if _requires_date_value(question)
            else "Retrieved chunks did not contain a sentence relevant enough to support an answer."
        )
        return AskResponse(
            answer=answer,
            sufficient_evidence=False,
            verification_status="insufficient_evidence",
            verification_note=verification_note,
            evidence=[],
            claims=[],
            conflicts=[],
        )

    evidence_responses = [
        EvidenceResponse(
            document_id=item.document_id,
            filename=item.filename,
            page_number=item.page_number,
            excerpt=item.text,
            retrieval_score=round(item.score, 3),
            status="retrieved",
        )
        for item in relevant_evidence
    ]

    conflicts = _find_conflicts(question, relevant_evidence)
    if conflicts:
        return AskResponse(
            answer="I cannot give a single answer because the uploaded documents conflict. Review both cited passages; the system cannot determine which source is correct.",
            sufficient_evidence=True,
            verification_status="contradicted",
            verification_note="Both retrieved passages are shown. Retrieval cannot resolve which source is accurate.",
            evidence=evidence_responses,
            claims=[],
            conflicts=conflicts,
        )

    generated_answer = _provider.answer(question, relevant_evidence)
    claims = _verify_claims(generated_answer, relevant_evidence)
    all_supported = bool(claims) and all(claim.status == "supported" for claim in claims)
    answer = (
        generated_answer
        if all_supported
        else "I cannot provide a supported answer from the cited passages. Unsupported claims are listed for review."
    )
    return AskResponse(
        answer=answer,
        sufficient_evidence=True,
        verification_status="supported" if all_supported else "unresolved",
        verification_note=(
            "Each answer claim matches its cited source text verbatim. This text-match check does not verify source authenticity or factual truth."
            if all_supported
            else "Retrieved passages do not support every generated claim. The answer has been withheld; inspect the unsupported claim labels."
        ),
        evidence=evidence_responses,
        claims=claims,
        conflicts=[],
    )