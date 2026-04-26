"""Unit tests for OCRService."""
import pathlib
import importlib.util
import pytest
import requests
from unittest.mock import patch, MagicMock

# Load module directly to avoid triggering the full core package __init__
# (which pulls in RAGService and its heavy ML deps)
_spec = importlib.util.spec_from_file_location(
    "ocr_service",
    pathlib.Path(__file__).parent.parent / "core" / "ocr_service.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
OCRService = _mod.OCRService

_PATCH_GET = "ocr_service.requests.get"
_PATCH_POST = "ocr_service.requests.post"


@pytest.fixture
def ocr():
    return OCRService(api_url="http://dots-ocr:8000", api_token="test-token")


class TestOCRServiceAvailability:

    def test_is_available_true_when_health_ok(self, ocr):
        with patch(_PATCH_GET) as mock_get:
            mock_get.return_value.status_code = 200
            assert ocr.is_available() is True
            mock_get.assert_called_once_with("http://dots-ocr:8000/health", timeout=5)

    def test_is_available_false_when_server_error(self, ocr):
        with patch(_PATCH_GET) as mock_get:
            mock_get.return_value.status_code = 503
            assert ocr.is_available() is False

    def test_is_available_false_on_connection_error(self, ocr):
        with patch(_PATCH_GET, side_effect=requests.ConnectionError):
            assert ocr.is_available() is False

    def test_is_available_false_on_timeout(self, ocr):
        with patch(_PATCH_GET, side_effect=requests.Timeout):
            assert ocr.is_available() is False

    def test_trailing_slash_stripped_from_url(self):
        svc = OCRService(api_url="http://dots-ocr:8000/", api_token="")
        with patch(_PATCH_GET) as mock_get:
            mock_get.return_value.status_code = 200
            svc.is_available()
            mock_get.assert_called_once_with("http://dots-ocr:8000/health", timeout=5)


class TestOCRServiceExtractText:

    def _make_response(self, text: str):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": text}}]
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_returns_extracted_text(self, ocr):
        with patch(_PATCH_POST) as mock_post:
            mock_post.return_value = self._make_response("Hello from OCR")
            result = ocr.extract_text_from_image(b"fake-image-bytes", "image/png")
        assert result == "Hello from OCR"

    def test_sends_authorization_header(self, ocr):
        with patch(_PATCH_POST) as mock_post:
            mock_post.return_value = self._make_response("text")
            ocr.extract_text_from_image(b"img", "image/png")
            _, kwargs = mock_post.call_args
            assert kwargs["headers"]["Authorization"] == "Bearer test-token"

    def test_no_auth_header_when_token_empty(self):
        svc = OCRService(api_url="http://ocr:8000", api_token="")
        with patch(_PATCH_POST) as mock_post:
            mock_post.return_value = self._make_response("text")
            svc.extract_text_from_image(b"img", "image/png")
            _, kwargs = mock_post.call_args
            assert "Authorization" not in kwargs["headers"]

    def test_payload_contains_base64_image(self, ocr):
        import base64
        image_bytes = b"fake-png-data"
        with patch(_PATCH_POST) as mock_post:
            mock_post.return_value = self._make_response("text")
            ocr.extract_text_from_image(image_bytes, "image/png")
            _, kwargs = mock_post.call_args
            messages = kwargs["json"]["messages"]
            image_content = messages[0]["content"][0]
            expected_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
            assert image_content["image_url"]["url"] == expected_url

    def test_posts_to_correct_endpoint(self, ocr):
        with patch(_PATCH_POST) as mock_post:
            mock_post.return_value = self._make_response("text")
            ocr.extract_text_from_image(b"img", "image/png")
            url = mock_post.call_args[0][0]
            assert url == "http://dots-ocr:8000/v1/chat/completions"

    def test_raises_on_http_error(self, ocr):
        with patch(_PATCH_POST) as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = requests.HTTPError("500")
            mock_post.return_value = mock_resp
            with pytest.raises(requests.HTTPError):
                ocr.extract_text_from_image(b"img", "image/png")
