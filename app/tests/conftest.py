"""Pytest configuration and fixtures."""
import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_pdf_path(temp_data_dir):
    """Path to a sample PDF (if it exists in data/)."""
    # Check if sample.pdf exists in the actual data directory
    real_data_dir = Path(__file__).parent.parent.parent.parent / "data"
    sample_pdf = real_data_dir / "sample.pdf"

    if sample_pdf.exists():
        return str(sample_pdf)
    return None


@pytest.fixture
def mock_documents():
    """Create mock documents for testing."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content="This is a test document about Python programming.",
            metadata={"source_file": "test1.pdf", "source_path": "/fake/path/test1.pdf", "page": 0}
        ),
        Document(
            page_content="This is another test document about machine learning.",
            metadata={"source_file": "test2.pdf", "source_path": "/fake/path/test2.pdf", "page": 0}
        ),
        Document(
            page_content="This document discusses data science and AI.",
            metadata={"source_file": "test3.pdf", "source_path": "/fake/path/test3.pdf", "page": 0}
        ),
    ]


@pytest.fixture
def config_env(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL_NAME", "llama2")
    monkeypatch.setenv("DATA_DIR", "data")
    monkeypatch.setenv("DEFAULT_TEMPERATURE", "0.1")
    monkeypatch.setenv("DEFAULT_CHUNK_SIZE", "1000")
    monkeypatch.setenv("DEFAULT_CHUNK_OVERLAP", "200")
    monkeypatch.setenv("DEFAULT_TOP_K", "4")
