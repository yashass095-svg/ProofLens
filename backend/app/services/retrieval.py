import re
from functools import lru_cache

from app.core.config import get_settings
from app.models.domain import DocumentRecord, ScoredEvidence

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }


class LexicalRetriever:
    """Dependency-free baseline retriever; scores are not confidence or truth values."""

    def retrieve(
        self, document: DocumentRecord, question: str, limit: int = 3
    ) -> list[ScoredEvidence]:
        query_tokens = _tokens(question)
        if not query_tokens:
            return []

        candidates: list[ScoredEvidence] = []
        for chunk in document.chunks:
            chunk_tokens = _tokens(chunk.text)
            overlap = len(query_tokens & chunk_tokens)
            score = overlap / len(query_tokens)
            if overlap:
                candidates.append(
                    ScoredEvidence(
                        document_id=document.document_id,
                        filename=document.filename,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        score=score,
                    )
                )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:limit]


@lru_cache
def _load_embedding_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class SentenceTransformersFaissRetriever:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def retrieve(
        self, document: DocumentRecord, question: str, limit: int = 3
    ) -> list[ScoredEvidence]:
        if not document.chunks:
            return []

        import faiss
        import numpy as np

        chunks = list(document.chunks)
        model = _load_embedding_model(self.model_name)
        vectors = model.encode(
            [chunk.text for chunk in chunks],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32, copy=False)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        query_vector = model.encode(
            [question], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32, copy=False)
        scores, indices = index.search(query_vector, min(limit, len(chunks)))

        return [
            ScoredEvidence(
                document_id=document.document_id,
                filename=document.filename,
                page_number=chunks[int(index)].page_number,
                text=chunks[int(index)].text,
                score=float(score),
            )
            for score, index in zip(scores[0], indices[0])
            if index >= 0
        ]


class ConfiguredRetriever:
    def __init__(self) -> None:
        self.lexical = LexicalRetriever()

    def retrieve(
        self, document: DocumentRecord, question: str, limit: int = 3
    ) -> list[ScoredEvidence]:
        settings = get_settings()
        if settings.retrieval_backend != "semantic":
            return self.lexical.retrieve(document, question, limit)
        try:
            retriever = SentenceTransformersFaissRetriever(settings.embedding_model)
            return retriever.retrieve(document, question, limit)
        except (ImportError, OSError, RuntimeError, ValueError):
            return self.lexical.retrieve(document, question, limit)