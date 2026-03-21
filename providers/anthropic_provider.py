"""
Anthropic (Claude) reasoning provider.

Requires the ``anthropic`` package::

    pip install anthropic

Set ANTHROPIC_API_KEY in the environment or pass api_key in the config.
"""

import base64
import mimetypes
from typing import Optional

from .base import BaseReasoningProvider


class AnthropicProvider(BaseReasoningProvider):
    """Text generation and vision via the Anthropic Messages API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250514",
    ):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "The 'anthropic' package is required for AnthropicProvider. "
                    "Install it with: pip install anthropic"
                )
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        client = self._get_client()
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

    def analyze_image(self, image_path: str, prompt: str) -> str:
        client = self._get_client()
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/png"
        with open(image_path, "rb") as f:
            image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.content[0].text

    @classmethod
    def from_config(cls, config: dict) -> "AnthropicProvider":
        return cls(
            api_key=config.get("api_key"),
            model=config.get("model", "claude-sonnet-4-5-20250514"),
        )
