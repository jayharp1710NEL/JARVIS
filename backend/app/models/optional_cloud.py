"""Optional cloud provider — DISABLED by default.

This exists so the system *can* use a frontier API when the user explicitly
opts in, but it is fenced behind ``ENABLE_CLOUD_MODE=true`` and never sees
private data (files/memory) unless ``allow_private_data_to_cloud`` is set.

It is an OpenAI-compatible client pointed at a cloud base URL.
"""
from __future__ import annotations

from ..config import Settings
from .base import HealthStatus, ModelError
from .openai_compatible import OpenAICompatibleProvider


class CloudDisabledError(ModelError):
    pass


class OptionalCloudProvider(OpenAICompatibleProvider):
    name = "cloud"

    def __init__(self, settings: Settings):
        if not settings.enable_cloud_mode:
            raise CloudDisabledError(
                "Cloud mode is disabled. Set ENABLE_CLOUD_MODE=true to enable "
                "it. JARVIS-LOCAL stays fully local by default."
            )
        if not settings.cloud_api_key:
            raise CloudDisabledError(
                "Cloud mode is enabled but CLOUD_API_KEY is empty. Provide a "
                "key in your environment to use the cloud provider."
            )
        super().__init__(
            base_url=settings.cloud_base_url,
            model=settings.cloud_model,
            api_key=settings.cloud_api_key,
            timeout=settings.request_timeout,
            provider_name="cloud",
        )
        self._allow_private = settings.allow_private_data_to_cloud

    @property
    def allows_private_data(self) -> bool:
        return self._allow_private

    def health_check(self) -> HealthStatus:
        status = super().health_check()
        status.detail = (
            "⚠ CLOUD MODE ACTIVE — requests leave your machine. " + status.detail
        )
        return status
