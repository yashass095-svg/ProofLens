from typing import Protocol

from app.models.domain import ScoredEvidence


class AnswerProvider(Protocol):
    def answer(self, question: str, evidence: list[ScoredEvidence]) -> str:
        """Draft a response from evidence without asserting independent verification."""


class ExtractiveAnswerProvider:
    def answer(self, question: str, evidence: list[ScoredEvidence]) -> str:
        if not evidence:
            return "I could not find enough relevant text in this document to answer."
        return evidence[0].text