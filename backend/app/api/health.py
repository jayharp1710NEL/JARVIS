"""Health & model info endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..models.router import build_provider
from ..web.search_providers import get_search_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    # Model provider health (never raises — returns a status object).
    try:
        provider = build_provider(settings.model_provider, settings)
        model_status = provider.health_check()
        model = {"ok": model_status.ok, "detail": model_status.detail, "provider": model_status.provider}
    except Exception as exc:  # noqa: BLE001 (e.g. cloud disabled)
        model = {"ok": False, "detail": str(exc), "provider": settings.model_provider}

    # Search provider availability (no network call for local).
    try:
        sp = get_search_provider(settings)
        ok, reason = sp.available()
        search = {"provider": sp.name, "ok": ok, "detail": reason or "configured"}
    except Exception as exc:  # noqa: BLE001
        search = {"provider": settings.search_provider, "ok": False, "detail": str(exc)}

    return {
        "status": "ok",
        "app": settings.app_name,
        "model": model,
        "search": search,
        "privacy": {
            "local_privacy_mode": settings.local_privacy_mode,
            "cloud_enabled": settings.enable_cloud_mode,
            "code_execution": settings.allow_code_execution,
        },
        "embeddings": settings.embedding_provider,
        "vector_store": settings.vector_store,
    }


@router.get("/models")
def models() -> dict:
    settings = get_settings()
    try:
        provider = build_provider(settings.model_provider, settings)
        return {"provider": settings.model_provider, "models": provider.list_models()}
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": settings.model_provider,
            "models": [],
            "error": str(exc),
        }
