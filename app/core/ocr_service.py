"""OCR service client for dots.ocr (OpenAI-compatible API)."""
import base64
import logging
import requests

logger = logging.getLogger(__name__)


class OCRService:
    """Client for the dots.ocr vision-language model API."""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.api_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def extract_text_from_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": "ocr",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                        {"type": "text", "text": "Extract all text from this image. Return only the extracted text."},
                    ],
                }
            ],
            "max_tokens": 4096,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        resp = requests.post(
            f"{self.api_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
