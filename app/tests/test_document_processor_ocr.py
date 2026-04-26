"""Tests for DocumentProcessor hybrid OCR logic."""
import io
import sys
import pathlib
import importlib.util
import pytest
from unittest.mock import MagicMock, patch

# Load modules directly to avoid triggering the full core package init
# (which would pull in RAGService and its heavy ML deps)
def _load_module(name, rel_path):
    spec = importlib.util.spec_from_file_location(
        name, pathlib.Path(__file__).parent.parent / rel_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_dp_mod = _load_module("document_processor", "core/document_processor.py")
_ocr_mod = _load_module("ocr_service", "core/ocr_service.py")
# Register in sys.modules so patch() can find them by name
sys.modules.setdefault("document_processor", _dp_mod)
sys.modules.setdefault("ocr_service", _ocr_mod)

DocumentProcessor = _dp_mod.DocumentProcessor
OCRService = _ocr_mod.OCRService

from langchain_core.documents import Document


def _make_ocr_service(available: bool = True, ocr_text: str = "OCR extracted text") -> OCRService:
    svc = MagicMock(spec=OCRService)
    svc.is_available.return_value = available
    svc.extract_text_from_image.return_value = ocr_text
    return svc


def _make_pdf_page(text: str, page: int = 0, filename: str = "test.pdf") -> Document:
    return Document(
        page_content=text,
        metadata={"source_file": filename, "source_path": f"/fake/{filename}", "page": page},
    )


class TestDocumentProcessorOCRInit:

    def test_default_no_ocr_service(self):
        processor = DocumentProcessor()
        assert processor.ocr_service is None
        assert processor.ocr_min_text_length == 50

    def test_custom_ocr_params(self):
        svc = _make_ocr_service()
        processor = DocumentProcessor(ocr_service=svc, ocr_min_text_length=100)
        assert processor.ocr_service is svc
        assert processor.ocr_min_text_length == 100


class TestDocumentProcessorOCRLogic:

    def _processor_with_mocked_pdf(self, pdf_pages, ocr_service=None, ocr_min_text_length=50):
        """Build a DocumentProcessor whose PyPDFLoader returns the given pages."""
        processor = DocumentProcessor(
            ocr_service=ocr_service,
            ocr_min_text_length=ocr_min_text_length,
        )
        mock_loader = MagicMock()
        mock_loader.load.return_value = pdf_pages
        return processor, mock_loader

    def test_rich_text_page_not_sent_to_ocr(self):
        page = _make_pdf_page("A" * 200)
        ocr_svc = _make_ocr_service()
        processor, mock_loader = self._processor_with_mocked_pdf([page], ocr_service=ocr_svc)

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        ocr_svc.extract_text_from_image.assert_not_called()
        assert docs[0].page_content == "A" * 200

    def test_sparse_page_sent_to_ocr_when_service_available(self):
        page = _make_pdf_page("tiny")  # len < 50
        ocr_svc = _make_ocr_service(available=True, ocr_text="Full OCR text")
        processor, mock_loader = self._processor_with_mocked_pdf([page], ocr_service=ocr_svc)

        fake_image = MagicMock()
        fake_image.save = lambda buf, format: buf.write(b"PNG_DATA")

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader), \
             patch.object(_dp_mod, "convert_from_path", return_value=[fake_image]):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        assert docs[0].page_content == "Full OCR text"
        assert docs[0].metadata.get("ocr") is True

    def test_sparse_page_not_sent_to_ocr_when_service_unavailable(self):
        page = _make_pdf_page("tiny")
        ocr_svc = _make_ocr_service(available=False)
        processor, mock_loader = self._processor_with_mocked_pdf([page], ocr_service=ocr_svc)

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        ocr_svc.extract_text_from_image.assert_not_called()
        assert docs[0].page_content == "tiny"
        assert "ocr" not in docs[0].metadata

    def test_no_ocr_service_configured(self):
        page = _make_pdf_page("tiny")
        processor, mock_loader = self._processor_with_mocked_pdf([page], ocr_service=None)

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        assert docs[0].page_content == "tiny"
        assert "ocr" not in docs[0].metadata

    def test_mixed_pages_only_sparse_get_ocr(self):
        pages = [
            _make_pdf_page("A" * 200, page=0),  # rich
            _make_pdf_page("x", page=1),         # sparse
            _make_pdf_page("B" * 200, page=2),  # rich
        ]
        ocr_svc = _make_ocr_service(available=True, ocr_text="OCR result")
        processor, mock_loader = self._processor_with_mocked_pdf(pages, ocr_service=ocr_svc)

        fake_image = MagicMock()
        fake_image.save = lambda buf, format: buf.write(b"PNG_DATA")

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader), \
             patch.object(_dp_mod, "convert_from_path", return_value=[fake_image]):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        assert docs[0].page_content == "A" * 200
        assert "ocr" not in docs[0].metadata

        assert docs[1].page_content == "OCR result"
        assert docs[1].metadata["ocr"] is True

        assert docs[2].page_content == "B" * 200
        assert "ocr" not in docs[2].metadata

        assert ocr_svc.extract_text_from_image.call_count == 1

    def test_ocr_failure_keeps_original_content(self):
        page = _make_pdf_page("tiny")
        ocr_svc = _make_ocr_service(available=True)
        ocr_svc.extract_text_from_image.side_effect = Exception("OCR API down")
        processor, mock_loader = self._processor_with_mocked_pdf([page], ocr_service=ocr_svc)

        fake_image = MagicMock()
        fake_image.save = lambda buf, format: buf.write(b"PNG_DATA")

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader), \
             patch.object(_dp_mod, "convert_from_path", return_value=[fake_image]):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        # should not crash and should keep original content
        assert docs[0].page_content == "tiny"
        assert "ocr" not in docs[0].metadata

    def test_source_metadata_always_added(self):
        page = _make_pdf_page("A" * 200)
        processor, mock_loader = self._processor_with_mocked_pdf([page])

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        assert docs[0].metadata["source_file"] == "test.pdf"
        assert docs[0].metadata["source_path"] == "/fake/test.pdf"

    def test_custom_min_text_length_respected(self):
        # 80 chars — above default 50 but below custom 100
        page = _make_pdf_page("A" * 80, page=0)
        ocr_svc = _make_ocr_service(available=True, ocr_text="OCR result")
        processor, mock_loader = self._processor_with_mocked_pdf(
            [page], ocr_service=ocr_svc, ocr_min_text_length=100
        )

        fake_image = MagicMock()
        fake_image.save = lambda buf, format: buf.write(b"PNG_DATA")

        with patch.object(_dp_mod, "PyPDFLoader", return_value=mock_loader), \
             patch.object(_dp_mod, "convert_from_path", return_value=[fake_image]):
            docs = processor._load_single_pdf("/fake/test.pdf", "test.pdf")

        assert docs[0].page_content == "OCR result"
        assert docs[0].metadata["ocr"] is True
