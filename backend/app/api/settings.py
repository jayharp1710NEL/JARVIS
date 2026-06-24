"""Settings API — view and update a safe subset of runtime configuration.

Updates are persisted to ``data/runtime_settings.json`` and applied to the
process environment, then settings are reloaded. Secrets are never returned in
GET responses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_settings, reload_settings

router = APIRouter(prefix="/settings", tags=["settings"])

# Keys the API is allowed to change (env var name -> type).
_EDITABLE: dict[str, type] = {
    "MODEL_PROVIDER": str,
    "OLLAMA_BASE_URL": str,
    "OLLAMA_MODEL": str,
    "OPENAI_BASE_URL": str,
    "OPENAI_MODEL": str,
    "SEARCH_PROVIDER": str,
    "SEARXNG_URL": str,
    "EMBEDDING_PROVIDER": str,
    "VECTOR_STORE": str,
    "TEMPERATURE": float,
    "MAX_TOKENS": int,
    "LOCAL_PRIVACY_MODE": bool,
    "ENABLE_CLOUD_MODE": bool,
    "ALLOW_PRIVATE_DATA_TO_CLOUD": bool,
    "ALLOW_CODE_EXECUTION": bool,
}
_SECRET_KEYS = {"BRAVE_API_KEY", "TAVILY_API_KEY", "SERPER_API_KEY", "CLOUD_API_KEY", "OPENAI_API_KEY"}


def runtime_file() -> Path:
    return get_settings().data_dir / "runtime_settings.json"


def load_runtime_overrides() -> None:
    """Apply persisted overrides to the environment (call at startup)."""
    p = runtime_file()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            for k, v in data.items():
                os.environ[k] = str(v)
        except Exception:
            pass


def _coerce(value, typ):
    if typ is bool:
        return str(value).lower() in ("1", "true", "yes", "on")
    return typ(value)


@router.get("")
def get_settings_view() -> dict:
    s = get_settings()
    return {
        "model_provider": s.model_provider,
        "ollama_base_url": s.ollama_base_url,
        "ollama_model": s.ollama_model,
        "openai_base_url": s.openai_base_url,
        "openai_model": s.openai_model,
        "search_provider": s.search_provider,
        "searxng_url": s.searxng_url,
        "embedding_provider": s.embedding_provider,
        "vector_store": s.vector_store,
        "temperature": s.temperature,
        "max_tokens": s.max_tokens,
        "local_privacy_mode": s.local_privacy_mode,
        "enable_cloud_mode": s.enable_cloud_mode,
        "allow_private_data_to_cloud": s.allow_private_data_to_cloud,
        "allow_code_execution": s.allow_code_execution,
        # report only whether secrets are configured, never the values
        "secrets_configured": {
            k.lower(): bool(os.environ.get(k)) for k in _SECRET_KEYS
        },
    }


class SettingsUpdate(BaseModel):
    updates: dict[str, str | float | int | bool]


@router.post("")
def update_settings(body: SettingsUpdate) -> dict:
    applied: dict[str, str] = {}
    p = runtime_file()
    current = {}
    if p.exists():
        try:
            current = json.loads(p.read_text())
        except Exception:
            current = {}

    for key, value in body.updates.items():
        env_key = key.upper()
        if env_key in _SECRET_KEYS:
            os.environ[env_key] = str(value)
            current[env_key] = str(value)
            applied[env_key] = "***"
            continue
        if env_key not in _EDITABLE:
            raise HTTPException(status_code=400, detail=f"Setting '{key}' is not editable.")
        coerced = _coerce(value, _EDITABLE[env_key])
        os.environ[env_key] = str(coerced)
        current[env_key] = str(coerced)
        applied[env_key] = str(coerced)

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current, indent=2))
    reload_settings()
    return {"applied": applied}
