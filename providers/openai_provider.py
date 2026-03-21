"""
OpenAI providers for text reasoning (GPT-4) and image generation (DALL-E).

Requires the ``openai`` package::

    pip install openai

Set OPENAI_API_KEY in the environment or pass api_key in the config.
"""

import base64
import mimetypes
from typing import Optional

from .base import BaseImageProvider, BaseReasoningProvider


class OpenAIReasoningProvider(BaseReasoningProvider):
    """Text generation and vision via the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for OpenAI providers. "
                    "Install it with: pip install openai"
                )
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def analyze_image(self, image_path: str, prompt: str) -> str:
        client = self._get_client()
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/png"
        with open(image_path, "rb") as f:
            image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content

    @classmethod
    def from_config(cls, config: dict) -> "OpenAIReasoningProvider":
        return cls(
            api_key=config.get("api_key"),
            model=config.get("model", "gpt-4o"),
        )


class OpenAIImageProvider(BaseImageProvider):
    """Image generation via the OpenAI Images API (DALL-E)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "dall-e-3",
        quality: str = "standard",
        style: str = "vivid",
    ):
        self.api_key = api_key
        self.model = model
        self.quality = quality
        self.default_style = style
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for OpenAI providers. "
                    "Install it with: pip install openai"
                )
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: Optional[str] = None,
    ) -> bytes:
        client = self._get_client()
        response = client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=self.quality,
            style=style or self.default_style,
            response_format="b64_json",
            n=1,
        )
        return base64.b64decode(response.data[0].b64_json)

    @classmethod
    def from_config(cls, config: dict) -> "OpenAIImageProvider":
        return cls(
            api_key=config.get("api_key"),
            model=config.get("model", "dall-e-3"),
            quality=config.get("quality", "standard"),
            style=config.get("style", "vivid"),
        )
