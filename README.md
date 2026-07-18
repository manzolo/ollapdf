# OllaPDF: Your Local Document Chat Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/manzolo/ollapdf/actions/workflows/test.yml/badge.svg)](https://github.com/manzolo/ollapdf/actions/workflows/test.yml)

OllaPDF is a locally-hosted document chat application. It allows you to ask questions about your PDF documents using Large Language Models via Ollama, keeping all data private on your own machine.

## Features

- **Intuitive Chat Interface:** Ask questions in natural language via Streamlit.
- **Local First:** All processing is done locally. Documents and queries never leave your machine.
- **Powered by Ollama:** Works with any model supported by Ollama (Llama, Mistral, Phi, etc.).
- **OCR Support:** Hybrid processing for scanned PDFs — native text extraction with automatic fallback to [dots.ocr](https://github.com/manzolo/dots.ocr) for image-only pages.
- **RAG Pipeline:** FAISS vector store + HuggingFace embeddings for accurate context retrieval.
- **Dockerized:** Runs fully containerized for easy setup.

## Screenshots

<img width="1880" height="977" alt="OllaPDF Screenshot 1" src="https://github.com/user-attachments/assets/5132217f-e056-42f5-82f1-66fb3d2e1d4d" />
<img width="1880" height="977" alt="OllaPDF Screenshot 2" src="https://github.com/user-attachments/assets/ad20b49f-d340-4adf-b162-e943731f8991" />
<img width="1880" height="977" alt="OllaPDF Screenshot 3" src="https://github.com/user-attachments/assets/b7742936-dc65-4235-8dd7-ad4569b9e62c" />
<img width="1880" height="977" alt="OllaPDF Screenshot 4" src="https://github.com/user-attachments/assets/c8a055d4-3cb0-4a44-b50d-b18e4640a72d" />

## How It Works

OllaPDF uses a RAG (Retrieval-Augmented Generation) architecture:

1. **Document Loading:** PDFs in `data/` are loaded. Native text is extracted via PyPDF; scanned pages (below the configurable text threshold) are sent to the OCR service if configured.
2. **Vector Embeddings:** Text chunks are converted to embeddings using a sentence-transformer model.
3. **Vector Store:** Embeddings are stored in a FAISS index for fast similarity search.
4. **Retrieval:** Your question is matched against the index to find the most relevant chunks.
5. **Generation:** The retrieved chunks are passed as context to an Ollama LLM, which generates the answer.

## Tech Stack

| Component | Technology |
|---|---|
| Web UI | Streamlit |
| LLM orchestration | LangChain |
| LLM provider | Ollama |
| Vector store | FAISS |
| Embeddings | sentence-transformers (HuggingFace) |
| OCR (optional) | dots.ocr via vLLM |
| Containerization | Docker |

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) + [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Clone the repository

```bash
git clone https://github.com/manzolo/ollapdf.git
cd ollapdf
```

### 2. Configure environment variables

```bash
cp .env.dist .env
```

Edit `.env` as needed:

```dotenv
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL_NAME=llama2
DEFAULT_TEMPERATURE=0.1
DEFAULT_CHUNK_SIZE=1000
DEFAULT_CHUNK_OVERLAP=200
DEFAULT_TOP_K=4

# OCR — optional, leave empty to disable
OCR_API_URL=
OCR_API_TOKEN=
OCR_MIN_TEXT_LENGTH=50
```

### 3. Add your PDFs

Place PDF files in the `data/` directory.

### 4. Start the application

**Option A — External Ollama (you already have it running):**
```bash
docker compose up -d --build
```

**Option B — CPU-only (Ollama + optional OCR in containers):**
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
```

**Option C — GPU / NVIDIA:**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```
> For the NVIDIA Container Toolkit setup see [this guide](https://www.manzolo.it/2025/11/installing-nvidia-container-toolkit/).

### 5. Pull an Ollama model

```bash
docker exec -it manzolo-ollapdf-ollama ollama pull llama2
```

### 6. Open the app

Navigate to `http://localhost:8501`.

## OCR for Scanned PDFs

OllaPDF supports automatic OCR via [dots.ocr](https://github.com/manzolo/dots.ocr), a vision-language model served through vLLM.

OCR is **opt-in**: set `OCR_API_URL` in your `.env` to enable it. When enabled, any PDF page with fewer than `OCR_MIN_TEXT_LENGTH` characters of native text is automatically converted to an image and sent to the OCR service.

The `docker-compose.cpu.yml` and `docker-compose.gpu.yml` files include a `dots-ocr` service. Build the CPU image first using the [dots-ocr-manager script](https://github.com/manzolo/dots.ocr).

## Useful Commands

```bash
# View app logs
docker logs -f manzolo-ollapdf-rag

# View Ollama logs
docker logs -f manzolo-ollapdf-ollama

# Stop all services
make down

# Open a shell in the app container
make shell

# List available Makefile targets
make help
```

## Testing

```bash
# Unit tests only (no external services needed)
docker build -t ollapdf-test . && docker run --rm ollapdf-test python -m pytest tests/ -v -m "not integration"

# Full integration tests (Ollama + OCR mock, auto-managed)
make test-integration-local
```

The CI pipeline runs automatically on every push:
- **unit-tests** — 43 tests, ~3 min, no external services
- **integration-tests** — OCR path (mock server) + RAG end-to-end (tinyllama), ~7 min

## Contributing

Pull requests and issues are welcome.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Streamlit](https://streamlit.io/)
- [LangChain](https://www.langchain.com/)
- [Ollama](https://ollama.ai/)
- [dots.ocr](https://github.com/manzolo/dots.ocr)

---

## 🧠 Local AI Lab

[![Local AI Lab](https://img.shields.io/badge/🧠_Local_AI_Lab-member-6e40c9?style=for-the-badge)](https://github.com/manzolo/local-ai-lab)

This project is part of **[manzolo's Local AI Lab](https://github.com/manzolo/local-ai-lab)** — a family of self-hosted AI projects (LLM, voice, vision & documents) that share the same conventions and can be wired together through the shared `local-ai-net` Docker network.

This repo ships a `docker-compose.local-ai.yml` override to join the shared network — see the [conventions](https://github.com/manzolo/local-ai-lab#conventions).

Explore the whole family: [`topic:local-ai`](https://github.com/search?q=user%3Amanzolo+topic%3Alocal-ai&type=repositories)
