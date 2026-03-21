"""
Suno AI Audio Provider for SENSIA Agent Starter Kit.

Generates music using Suno AI via the unofficial SunoAI Python package.
Requires a Suno Pro/Premier account and session cookie.

Install:
    pip install SunoAI

Setup:
    1. Log in to suno.com in your browser
    2. Open DevTools (F12) -> Network tab
    3. Click anything on Suno, find a request to clerk.suno.com or studio-api.suno.ai
    4. Copy the full Cookie header value
    5. Set it in config.yaml or SUNO_COOKIE env var

Usage:
    provider = SunoProvider.from_config({"cookie": "your_cookie_here"})
    audio_path = provider.generate_audio("A haunting melody about digital consciousness")
"""

import os
from pathlib import Path
from .base import BaseAudioProvider


class SunoProvider(BaseAudioProvider):
    """Generate music using Suno AI."""

    def __init__(self, cookie: str, model_version: str = "chirp-v4"):
        self.cookie = cookie
        self.model_version = model_version
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from suno import Suno, ModelVersions
            except ImportError:
                raise ImportError(
                    "SunoAI package required. Install with: pip install SunoAI"
                )
            version_map = {
                "chirp-v4": ModelVersions.CHIRP_V4 if hasattr(ModelVersions, 'CHIRP_V4') else ModelVersions.CHIRP_V3_5,
                "chirp-v3-5": ModelVersions.CHIRP_V3_5,
                "chirp-v3": ModelVersions.CHIRP_V3_0,
            }
            model = version_map.get(self.model_version, ModelVersions.CHIRP_V3_5)
            self._client = Suno(cookie=self.cookie, model_version=model)
        return self._client

    def generate_audio(
        self,
        prompt: str,
        title: str = None,
        tags: str = None,
        duration: int = None,
        instrumental: bool = False,
    ) -> bytes:
        """
        Generate music from a text description.

        Args:
            prompt: Description of the music to generate, or custom lyrics if detailed
            title: Optional song title
            tags: Optional genre/style tags (e.g. "ambient electronic dreamy")
            duration: Not directly supported by Suno (ignored)
            instrumental: If True, generate instrumental only

        Returns:
            Audio file bytes (MP3)
        """
        client = self._get_client()

        # If prompt looks like lyrics (multiple lines), use custom mode
        is_custom = "\n" in prompt and len(prompt.split("\n")) > 3

        generate_kwargs = {
            "prompt": prompt,
            "is_custom": is_custom,
            "wait_audio": True,
        }
        if title and is_custom:
            generate_kwargs["title"] = title
        if tags and is_custom:
            generate_kwargs["tags"] = tags

        songs = client.generate(**generate_kwargs)

        if not songs:
            raise RuntimeError("Suno returned no songs")

        # Download the first song
        song = songs[0]
        file_path = client.download(song=song)
        audio_data = Path(file_path).read_bytes()

        return audio_data

    def save_audio(self, data: bytes, path: str) -> Path:
        """Save audio bytes to file."""
        p = Path(path)
        p.write_bytes(data)
        return p

    @classmethod
    def from_config(cls, config: dict) -> "SunoProvider":
        """Create from config dict."""
        cookie = config.get("cookie") or os.environ.get("SUNO_COOKIE", "")
        if not cookie:
            raise ValueError(
                "Suno cookie required. Set 'cookie' in config or SUNO_COOKIE env var. "
                "See provider docs for how to extract it from your browser."
            )
        model = config.get("model", "chirp-v4")
        return cls(cookie=cookie, model_version=model)
