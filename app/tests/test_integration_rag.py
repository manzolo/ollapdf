"""Integration tests for the complete RAG pipeline (requires Ollama)."""
import pytest
import tempfile
from pathlib import Path


def _ollama_available() -> bool:
    import requests
    from config import config
    try:
        r = requests.get(f"{config.ollama_host}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _create_sample_pdf(path: Path) -> None:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in [
        "This document is about Python programming.",
        "Python is a high-level, interpreted programming language.",
        "It is widely used for web development, data science, and automation.",
    ]:
        pdf.cell(0, 10, line)
        pdf.ln()
    pdf.output(str(path))


@pytest.mark.integration
class TestRAGIntegration:

    def test_rag_end_to_end(self):
        if not _ollama_available():
            pytest.skip("Ollama not reachable")

        from core import DocumentProcessor, RAGService
        from config import config

        with tempfile.TemporaryDirectory() as tmpdir:
            _create_sample_pdf(Path(tmpdir) / "test.pdf")

            processor = DocumentProcessor(
                chunk_size=config.default_chunk_size,
                chunk_overlap=config.default_chunk_overlap,
            )
            documents = processor.load_documents(tmpdir)
            assert len(documents) > 0, "No documents loaded from sample PDF"

            rag = RAGService(
                embedding_model=config.embedding_model,
                ollama_host=config.ollama_host,
                model_name=config.ollama_model_name,
                temperature=config.default_temperature,
                top_k=config.default_top_k,
                timeout=config.llm_timeout,
            )
            chain = rag.initialize(documents)
            assert chain is not None, "RAG chain initialization failed"

            response = rag.query("What is this document about?")
            assert response is not None
            assert len(response.get("answer", "")) > 0, "Empty answer from model"
