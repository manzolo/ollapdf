# OllaPDF — Codebase Guide for Claude

## What this project does

Streamlit app that lets users chat with local PDF documents via a RAG pipeline. LLM inference via Ollama, vector search via FAISS, optional OCR for scanned PDFs via dots.ocr.

## Architecture

```
app/
  main.py                  # Streamlit entry point, wires everything together
  config/
    settings.py            # AppConfig dataclass, load_config() reads env vars
  core/
    document_processor.py  # PDF loading, hybrid OCR logic, chunking
    ocr_service.py         # HTTP client for dots.ocr (OpenAI-compatible API)
    rag_service.py         # FAISS vector store + LangChain RAG chain
  services/
    request_queue.py       # Concurrent request throttling
  ui/
    text_processing.py     # LaTeX rendering, <think> tag stripping, cleanup
    styling.py             # Streamlit CSS
  tests/
    test_document_processor.py      # unit
    test_document_processor_ocr.py  # unit — OCR decision logic
    test_ocr_service.py             # unit — HTTP client
    test_request_queue.py           # unit + integration marker
    test_text_processing.py         # unit
    test_integration_rag.py         # integration — real Ollama (tinyllama)
    test_integration_ocr.py         # integration — scanned PDF + mock OCR server
```

## Key flows

**PDF loading with OCR fallback** (`document_processor.py:_load_single_pdf`):
1. PyPDFLoader extracts text from each page
2. If `len(text) < ocr_min_text_length` AND `ocr_service.is_available()` → convert page to PNG via `pdf2image` → POST to dots.ocr API → replace page content
3. `doc.metadata['ocr'] = True` marks OCR-processed pages

**OCR service** (`ocr_service.py`): OpenAI-compatible `/v1/chat/completions` POST with base64 image. Health check on `/health`.

**RAG chain** (`rag_service.py`): HuggingFace embeddings → FAISS index → LangChain retrieval chain → ChatOllama.

**Config** (`config/settings.py`): all settings come from env vars with sane defaults. `config` is a module-level singleton imported everywhere.

## Docker compose files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Base: ollapdf app only |
| `docker-compose.cpu.yml` | Adds: ollama (CPU) + dots-ocr-cpu |
| `docker-compose.gpu.yml` | Adds: ollama (GPU) + dots-ocr (GPU/vLLM) |
| `docker-compose.ci.yml` | CI override: adds ollama, disables OCR (`OCR_API_URL=`) |

## CI pipeline (`.github/workflows/test.yml`)

Two sequential jobs:
1. **unit-tests** — `docker build` + `pytest -m "not integration"` (43 tests, ~3 min)
2. **integration-tests** — full stack via `docker-compose.ci.yml` with `OLLAMA_MODEL_NAME=tinyllama`:
   - OCR path: image-only PDF + in-process mock HTTP server → verifies `metadata['ocr']=True`
   - RAG path: real Ollama query → verifies non-empty answer

## Testing locally

```bash
# Unit tests (fast, no services)
docker build -t ollapdf-test . && docker run --rm ollapdf-test python -m pytest tests/ -v -m "not integration"

# Integration tests (starts Ollama + tinyllama, tears down after)
make test-integration-local
```

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | |
| `OLLAMA_MODEL_NAME` | `llama2` | |
| `DEFAULT_TEMPERATURE` | `0.1` | |
| `DEFAULT_CHUNK_SIZE` | `1000` | |
| `DEFAULT_CHUNK_OVERLAP` | `200` | |
| `DEFAULT_TOP_K` | `4` | |
| `OCR_API_URL` | `` (empty) | Leave empty to disable OCR |
| `OCR_API_TOKEN` | `` | Bearer token for dots.ocr |
| `OCR_MIN_TEXT_LENGTH` | `50` | Pages below this char count trigger OCR |
| `LLM_TIMEOUT` | `300` | Seconds |

## Important constraints

- `dots-ocr-cpu:v0.11.1` is a locally-built image (vLLM compiled from source, ~15-30 min). It cannot be built in CI. Use `make test-integration-local` with OCR disabled for CI-equivalent testing, or run the real dots-ocr service locally.
- The `data/` directory is mounted as a volume; place PDFs there before starting the app.
- `pytest.ini` sets `testpaths = tests` — run pytest from `app/` or via `docker exec`.
