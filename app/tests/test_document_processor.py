"""Unit tests for DocumentProcessor."""
import pytest
import os
from core.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        processor = DocumentProcessor()
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        processor = DocumentProcessor(chunk_size=500, chunk_overlap=100)
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 100

    def test_find_pdf_files_empty_dir(self, temp_data_dir):
        """Test finding PDFs in empty directory."""
        processor = DocumentProcessor()
        pdf_files = processor._find_pdf_files(temp_data_dir)
        assert len(pdf_files) == 0

    def test_get_document_stats_empty_dir(self, temp_data_dir):
        """Test getting stats from empty directory."""
        stats = DocumentProcessor.get_document_stats(temp_data_dir)
        assert stats['total_files'] == 0
        assert stats['pdf_count'] == 0
        assert stats['total_size_mb'] == 0
        assert len(stats['pdf_files']) == 0

    def test_get_document_stats_nonexistent_dir(self):
        """Test getting stats from nonexistent directory."""
        stats = DocumentProcessor.get_document_stats("/nonexistent/path")
        assert stats['total_files'] == 0

    def test_load_documents_empty_dir(self, temp_data_dir):
        """Test loading documents from empty directory."""
        processor = DocumentProcessor()
        docs = processor.load_documents(temp_data_dir)
        assert len(docs) == 0

    def test_load_documents_nonexistent_dir(self):
        """Test loading documents from nonexistent directory."""
        processor = DocumentProcessor()
        docs = processor.load_documents("/nonexistent/path")
        assert len(docs) == 0
