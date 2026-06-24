"""Small utility tools: datetime and system_health."""
from __future__ import annotations

import datetime as _dt
import platform

from pydantic import BaseModel

from ..config import get_settings
from .base import Tool


class DatetimeInput(BaseModel):
    timezone_offset_hours: float = 0.0


class DatetimeTool(Tool):
    name = "datetime"
    description = "Get the current local date and time (UTC + optional offset)."
    InputModel = DatetimeInput

    def execute(self, params: DatetimeInput):
        now = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(
            hours=params.timezone_offset_hours
        )
        data = {
            "iso": now.isoformat(),
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "utc_offset_hours": params.timezone_offset_hours,
        }
        return data, now.isoformat()


class SystemHealthInput(BaseModel):
    pass


class SystemHealthTool(Tool):
    name = "system_health"
    description = "Report local system + provider configuration health."
    InputModel = SystemHealthInput

    def execute(self, params: SystemHealthInput):
        settings = get_settings()
        data = {
            "app": settings.app_name,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "model_provider": settings.model_provider,
            "ollama_model": settings.ollama_model,
            "search_provider": settings.search_provider,
            "vector_store": settings.vector_store,
            "embedding_provider": settings.embedding_provider,
            "local_privacy_mode": settings.local_privacy_mode,
            "cloud_enabled": settings.enable_cloud_mode,
            "code_execution": settings.allow_code_execution,
        }
        return data, "system health collected"
