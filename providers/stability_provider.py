"""
Stability AI image generation provider.

Uses the Stability AI REST API. Requires the ``requests`` package and a
Stability API key (set STABILITY_API_KEY or pass api_key in config).
"""

from typing import Optional

from .base import BaseImageProvider


_API_HOST = "https://api.stability.ai"


class StabilityProvider(BaseImageProvider):
    """Image generation via the Stability AI REST API.

    No proprietary SDK required -- only ``requests``.
    """

    def __init__(
        self,
        api_key: str,
        engine: str = "stable-diffusion-xl-1024-v1-0",
    ):
        self.api_key = api_key
        self.engine = engine

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: Optional[str] = None,
    ) -> bytes:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "The 'requests' package is required for StabilityProvider. "
                "Install it with: pip install requests"
            )
        width, height = (int(d) for d in size.split("x"))
        body = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "width": width,
            "height": height,
            "samples": 1,
            "steps": 30,
        }
        if style:
            body["style_preset"] = style
        url = f"{_API_HOST}/v1/generation/{self.engine}/text-to-image"
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
            timeout=120,
        )
        response.raise_for_status()
        import base64
        data = response.json()
        return base64.b64decode(data["artifacts"][0]["base64"])

    @classmethod
    def from_config(cls, config: dict) -> "StabilityProvider":
        api_key = config.get("api_key", "")
        if not api_key:
            import os
            api_key = os.environ.get("STABILITY_API_KEY", "")
        return cls(
            api_key=api_key,
            engine=config.get("engine", "stable-diffusion-xl-1024-v1-0"),
        )
