# ProofLens AI

ProofLens AI is a small, evidence-grounded PDF question-answering starter for hackathon Track 2, problem O3. It extracts page-aware text, retrieves relevant excerpts, and reports when the indexed text does not offer enough support.

**Retrieval is not verification.** The default response is extractive. Claims are marked supported only when their text matches a retrieved source passage verbatim; this does not authenticate the source or prove factual truth. Unsupported generated claims are withheld, and conflicting dates/numbers across uploaded PDFs cause an abstention.

## Requirements

- Windows 10/11, PowerShell, and Python 3.11+
- Node.js 20+
- Python packages and pip cache remain on E: using the commands below

## Run on Windows PowerShell

Open two PowerShell terminals in `E:\ProofLens-AI`.

### Backend

```powershell
Set-Location E:\ProofLens-AI\backend
py -3.11 -m venv E:\ProofLens-AI\backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& E:\ProofLens-AI\backend\.venv\Scripts\Activate.ps1
$env:PIP_CACHE_DIR = 'E:\pip-cache'
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is at `http://127.0.0.1:8000`; interactive docs are at `http://127.0.0.1:8000/docs`.

Run backend tests in another backend terminal after activating the environment:

```powershell
Set-Location E:\ProofLens-AI\backend
& E:\ProofLens-AI\backend\.venv\Scripts\Activate.ps1
python -m pytest
```

### Frontend

```powershell
Set-Location E:\ProofLens-AI\frontend
$env:npm_config_cache = 'E:\npm-cache'
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). Vite proxies `/api` requests to the backend.

## Features

- First-visit cinematic intro with skip/continue actions; it is remembered in browser storage and skipped when reduced motion is requested.
- Drag-and-drop PDF upload with the existing five-document and 20 MB limits, truthful per-file processing labels, and accessible errors.
- Upload and compare up to five PDFs per question, with a 20 MB per-file limit.
- Retrieve sentence-level excerpts with their source filename and original page number.
- Click a citation to view the rendered source PDF page and exact excerpt. The viewer does not claim to highlight text on the page.
- Download a paginated PDF report generated from the currently displayed question and result, including evidence and any conflicts.
- For deadline/date questions, prioritize sentences containing a date value; a keyword-only mention is not enough to answer with a date.
- Abstain when the requested field is marked unavailable or no supporting value is found.
- Show both sources and abstain when different documents give conflicting dates or numeric values.
- Keep retrieval, answer providers, PDF processing, API schemas, and UI components in separate modules.

Retrieval scores rank candidate passages; they are not confidence estimates. A `supported` claim is checked against its cited passage, but that text match does not establish source authenticity or factual truth.

## Architecture

The API extracts page-preserving text with PyMuPDF, chunks it per page, and stores both document records and original PDF bytes in process memory. The citation page endpoint renders a requested page to PNG using the document UUID; report PDFs are generated from the current question/result payload using PyMuPDF. The default lexical retriever works without model downloads. Optional Sentence Transformers + FAISS retrieval can be enabled with `RETRIEVAL_BACKEND=semantic`; its model downloads on first use. The QA service filters to relevant sentences, checks answer claims against citations, and detects a limited class of cross-document date/numeric conflicts.

To install and enable semantic retrieval in the active E-drive virtual environment:

```powershell
Set-Location E:\ProofLens-AI\backend
$env:PIP_CACHE_DIR = 'E:\pip-cache'
python -m pip install -r requirements-ml.txt
$env:RETRIEVAL_BACKEND = 'semantic'
```

The selected embedding model downloads when semantic retrieval is first used.

See [docs/architecture.md](docs/architecture.md) for the request flow and extension boundaries.

## Testing

Run the backend suite from an activated `backend\.venv`:

```powershell
Set-Location E:\ProofLens-AI\backend
& E:\ProofLens-AI\backend\.venv\Scripts\Activate.ps1
python -m pytest
```

The suite covers supported answers, abstention, conflicts, page-to-source mapping, downloadable reports for supported/insufficient/conflict results, and pagination of long report excerpts.

Build-check the frontend:

```powershell
Set-Location E:\ProofLens-AI\frontend
npm run build
```

## Limitations

- Documents are in-memory and are lost when the backend restarts. The starter is single-process; do not use multiple workers expecting shared document state.
- There is no authentication, user isolation, durable storage, rate limiting, or general-purpose contradiction/entailment model.
- Citation page images are available to anyone who possesses the corresponding unguessable in-memory document ID. Add authentication and per-user ownership checks before exposing private uploads beyond a trusted demo.
- Cited excerpts are shown beside the rendered PDF page; there is no in-page highlight because text-to-pixel mapping is not reliable for arbitrary PDF layouts.
- Conflict detection is heuristic and limited to relevant date/numeric values across different PDFs.
- The default answer provider is extractive. No generative model is connected; the provider interface is an extension point.
- The optional semantic retriever may fall back to lexical retrieval if its model or packages are unavailable.

## Deployment

For a demo, build the frontend and run the API locally:

```powershell
Set-Location E:\ProofLens-AI\frontend
npm run build

Set-Location E:\ProofLens-AI\backend
& E:\ProofLens-AI\backend\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For a hosted demo, the included `Dockerfile` builds the frontend and serves it from the FastAPI application, so the UI and `/api` share one HTTPS origin. `render.yaml` defines this as a Render web service with `/api/health` as its health check. The current starter is not production-hardened: add authentication, per-user document isolation, persistent storage, request limits, and operational monitoring before exposing private documents publicly.
