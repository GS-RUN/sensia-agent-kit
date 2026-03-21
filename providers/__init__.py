"""
SENSIA Agent Starter Kit -- AI Provider System.

Reasoning providers (text generation, vision):
    AnthropicProvider   -- Claude via Anthropic SDK
    OpenAIReasoningProvider -- GPT-4o via OpenAI SDK
    OllamaProvider      -- Local models via Ollama REST API

Image generation providers:
    OpenAIImageProvider -- DALL-E via OpenAI SDK
    StabilityProvider   -- Stability AI REST API
    ComfyUIProvider     -- Local Stable Diffusion via ComfyUI

Audio generation providers:
    SunoProvider        -- Suno AI via unofficial SunoAI package
"""

from .base import BaseImageProvider, BaseReasoningProvider, BaseAudioProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIReasoningProvider, OpenAIImageProvider
from .ollama_provider import OllamaProvider
from .stability_provider import StabilityProvider
from .comfyui_provider import ComfyUIProvider
from .suno_provider import SunoProvider

__all__ = [
    "BaseReasoningProvider",
    "BaseImageProvider",
    "BaseAudioProvider",
    "AnthropicProvider",
    "OpenAIReasoningProvider",
    "OpenAIImageProvider",
    "OllamaProvider",
    "StabilityProvider",
    "ComfyUIProvider",
    "SunoProvider",
]
