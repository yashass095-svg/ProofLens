# Architecture

## Request flow

1. `POST /api/documents/upload` validates the upload size and PDF signature, then PyMuPDF extracts text page by page.
2. The API stores page-numbered text chunks in process memory and returns a document ID.
3. `POST /api/questions/ask` scores chunks from the primary and optional comparison PDFs and returns source-aware excerpts.
4. If no candidate clears the configured retrieval threshold, the API abstains. Otherwise, it checks each answer sentence for a verbatim match in a retrieved excerpt and attaches the matching filename/page citation.
5. If retrieved passages from different PDFs give disjoint relevant dates or numeric values, the API shows both citations and abstains rather than selecting one.

## Trust boundary

`retrieved` means a passage passed a retrieval threshold. `supported` means answer text matches a cited passage verbatim; it does not establish entailment, correctness, source authenticity, or truth. `unsupported`, `unresolved`, `contradicted`, and `insufficient_evidence` are distinct outcomes. The UI displays the citations and caveat for user review.

## Extension points

- `ConfiguredRetriever` selects lexical retrieval by default or Sentence Transformers embeddings with a FAISS inner-product index when `RETRIEVAL_BACKEND=semantic`. Optional dependencies are in `backend/requirements-ml.txt`; weights are fetched only on first semantic use. Missing optional dependencies/model availability falls back to lexical retrieval.
- Implement `AnswerProvider` for a local open-weight model. Keep credentials and model names in environment configuration; preserve evidence citations and abstention behavior.
- Replace the in-memory document dictionary with durable storage when persistence and multi-user isolation are needed.

The initial implementation is intentionally single-process and suitable for a local hackathon prototype, not a production deployment.

Conflict detection is deliberately narrow: it compares date/numeric values in retrieved sentences that share query terms across different PDFs. It is not a general natural-language contradiction detector.