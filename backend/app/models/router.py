"""Model router — selects and instantiates the active provider.

Keeps providers swappable and applies the privacy guard before ever handing
out the cloud provider.
"""
from __future__ import annotations

from typing import Optional

from ..config import Settings, get_settings
from .base import GenSettings, ModelProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .optional_cloud import CloudDisabledError, OptionalCloudProvider


def build_provider(name: str, settings: Settings) -> ModelProvider:
    name = (name or settings.model_provider).lower()
    if name == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.request_timeout,
        )
    if name in ("openai_compatible", "openai", "local"):
        return OpenAICompatibleProvider(
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout,
        )
    if name == "cloud":
        # Raises CloudDisabledError unless explicitly enabled.
        return OptionalCloudProvider(settings)
    raise ValueError(f"Unknown model provider: {name}")


class ModelRouter:
    """Resolves provider/model overrides from request settings."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def get(self, provider: Optional[str] = None, model: Optional[str] = None) -> ModelProvider:
        prov = build_provider(provider or self.settings.model_provider, self.settings)
        if model:
            prov.model = model  # type: ignore[attr-defined]
        return prov

    def gen_settings(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenSettings:
        return GenSettings(
            temperature=temperature if temperature is not None else self.settings.temperature,
            top_p=top_p if top_p is not None else self.settings.top_p,
            max_tokens=max_tokens if max_tokens is not None else self.settings.max_tokens,
        )

    def is_cloud(self, provider: Optional[str]) -> bool:
        return (provider or self.settings.model_provider).lower() == "cloud"


__all__ = [
    "ModelRouter",
    "build_provider",
    "CloudDisabledError",
]
