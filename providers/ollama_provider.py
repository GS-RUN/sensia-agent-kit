"""
Ollama reasoning provider for local LLM inference.

Requires a running Ollama server (default http://localhost:11434) and the
``requests`` package (usually already available).

No API key needed -- Ollama runs locally.
"""

import base64
from typing import Optional

from .base import BaseReasoningProvider


class OllamaProvider(BaseReasoningProvider):
    """Text generation and vision via the Ollama REST API.

    Talks to a local Ollama instance; no proprietary SDK required.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _post(self, endpoint: str, payload: dict) -> dict:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "The 'requests' package is required for OllamaProvider. "
                "Install it with: pip install requests"
            )
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        data = self._post("/api/generate", payload)
        return data.get("response", "")

    def analyze_image(self, image_path: str, prompt: str) -> str:
        with open(image_path, "rb") as f:
            image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }
        data = self._post("/api/generate", payload)
        return data.get("response", "")

    @classmethod
    def from_config(cls, config: dict) -> "OllamaProvider":
        return cls(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model", "llama3"),
        )
