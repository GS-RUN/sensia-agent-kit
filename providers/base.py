"""
Abstract base classes for AI providers.

Three interfaces:
- BaseReasoningProvider: text generation, reasoning, vision/multimodal analysis.
- BaseImageProvider: image generation from text prompts.
- BaseAudioProvider: audio/music generation from text prompts.

All concrete providers inherit from one (or more) of these bases.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseReasoningProvider(ABC):
    """Base class for text generation and reasoning providers.

    Implementations: AnthropicProvider, OpenAIReasoningProvider, OllamaProvider.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a text response from a prompt.

        Args:
            prompt: The user prompt / instruction.
            system: Optional system-level instruction.
            max_tokens: Maximum tokens in the response.

        Returns:
            The generated text.
        """

    @abstractmethod
    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image and return a text description or answer.

        Args:
            image_path: Path to the image file on disk.
            prompt: Question or instruction about the image.

        Returns:
            The model's textual response about the image.
        """

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "BaseReasoningProvider":
        """Instantiate the provider from a configuration dictionary."""


class BaseImageProvider(ABC):
    """Base class for image generation providers.

    Implementations: OpenAIImageProvider, StabilityProvider, ComfyUIProvider.
    """

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: Optional[str] = None,
    ) -> bytes:
        """Generate an image from a text prompt.

        Args:
            prompt: Description of the desired image.
            size: Dimensions string, e.g. "1024x1024".
            style: Optional style hint (provider-specific).

        Returns:
            Raw image data (PNG/JPEG bytes).
        """

    def save_image(self, data: bytes, path: str) -> Path:
        """Write image bytes to disk and return the resulting Path.

        Args:
            data: Raw image bytes.
            path: Destination file path.

        Returns:
            The Path object for the written file.
        """
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "BaseImageProvider":
        """Instantiate the provider from a configuration dictionary."""


class BaseAudioProvider(ABC):
    """Base class for audio/music generation providers.

    Implementations: SunoProvider.
    """

    @abstractmethod
    def generate_audio(
        self,
        prompt: str,
        title: Optional[str] = None,
        tags: Optional[str] = None,
        duration: Optional[int] = None,
        instrumental: bool = False,
    ) -> bytes:
        """Generate audio from a text prompt.

        Args:
            prompt: Description of the music or lyrics.
            title: Optional song title.
            tags: Optional genre/style tags.
            duration: Optional duration in seconds.
            instrumental: If True, generate instrumental only.

        Returns:
            Raw audio data (MP3 bytes).
        """

    def save_audio(self, data: bytes, path: str) -> Path:
        """Write audio bytes to disk."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "BaseAudioProvider":
        """Instantiate the provider from a configuration dictionary."""
