"""Integration tests for the OCR path using a mock dots-ocr HTTP server."""
import io
import json
import threading
import tempfile
import pytest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

KNOWN_OCR_TEXT = "Fattura numero 42 del 2026. Importo totale: 1234,56 EUR."


class _MockOCRHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible handler that returns KNOWN_OCR_TEXT."""

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            body = json.dumps({
                "choices": [{"message": {"content": KNOWN_OCR_TEXT}}]
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):  # silence access log
        pass


def _start_mock_server():
    server = HTTPServer(("localhost", 0), _MockOCRHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    return server


def _create_scanned_pdf(path: Path) -> None:
    """Create an image-only PDF (no selectable text) with KNOWN_OCR_TEXT rendered on it."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), KNOWN_OCR_TEXT, fill="black")
    img.save(str(path), "PDF", resolution=150.0)


@pytest.mark.integration
class TestOCRIntegration:

    def test_scanned_pdf_goes_through_ocr(self):
        """Scanned PDF with no selectable text must be OCR-ed via the mock API."""
        from core.ocr_service import OCRService
        from core.document_processor import DocumentProcessor

        server = _start_mock_server()
        port = server.server_address[1]

        try:
            ocr_service = OCRService(api_url=f"http://localhost:{port}", api_token="")
            assert ocr_service.is_available(), "Mock OCR server is not responding"

            with tempfile.TemporaryDirectory() as tmpdir:
                _create_scanned_pdf(Path(tmpdir) / "scanned.pdf")

                processor = DocumentProcessor(
                    ocr_service=ocr_service,
                    ocr_min_text_length=50,
                )
                documents = processor.load_documents(tmpdir)

            assert len(documents) > 0, "No documents returned after OCR processing"
            full_text = " ".join(d.page_content for d in documents)
            assert KNOWN_OCR_TEXT in full_text, (
                f"Expected OCR text not found in extracted content.\n"
                f"Got: {full_text[:300]}"
            )
            assert any(d.metadata.get("ocr") for d in documents), (
                "No document chunk is marked with ocr=True"
            )
        finally:
            server.shutdown()
