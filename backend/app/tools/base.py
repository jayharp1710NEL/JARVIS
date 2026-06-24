"""Tool base class and result types.

Every tool: declares a name/description, validates input via a Pydantic model,
declares required permissions, and returns a structured ``ToolResult``. The
base ``run`` wrapper handles timing, permission checks and error capture so
individual tools stay small.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from ..security.permissions import Permission, PermissionContext, PermissionDenied


class ToolResult(BaseModel):
    ok: bool
    tool: str
    data: Any = None
    summary: str = ""
    error: str | None = None
    duration_ms: float = 0.0


class Tool(ABC):
    name: str = "tool"
    description: str = ""
    permissions: list[Permission] = []
    InputModel: Type[BaseModel] = BaseModel

    @abstractmethod
    def execute(self, params: BaseModel) -> tuple[Any, str]:
        """Return (data, human_summary). Raise on failure."""

    def input_schema(self) -> dict:
        return self.InputModel.model_json_schema()

    def run(self, raw_params: dict, ctx: PermissionContext | None = None) -> ToolResult:
        start = time.perf_counter()
        try:
            params = self.InputModel(**(raw_params or {}))
        except ValidationError as exc:
            return ToolResult(
                ok=False, tool=self.name, error=f"Invalid input: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        try:
            if ctx is not None and self.permissions:
                ctx.require(*self.permissions)
            data, summary = self.execute(params)
            return ToolResult(
                ok=True, tool=self.name, data=data, summary=summary,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except PermissionDenied as exc:
            return ToolResult(ok=False, tool=self.name, error=str(exc),
                              duration_ms=(time.perf_counter() - start) * 1000)
        except Exception as exc:  # noqa: BLE001 — tools must fail gracefully
            return ToolResult(ok=False, tool=self.name, error=str(exc),
                              duration_ms=(time.perf_counter() - start) * 1000)
