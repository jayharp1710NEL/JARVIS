"""ToolRegistry — registers and dispatches tools with logging + permissions."""
from __future__ import annotations

import logging

from ..agent.schemas import ToolCallTrace
from ..security.permissions import PermissionContext
from .base import Tool, ToolResult
from .calculator import CalculatorTool
from .extras import DatetimeTool, SystemHealthTool
from .file_tools import LocalFileIngestTool, LocalFileSearchTool
from .memory_tools import (
    MemoryDeleteTool,
    MemoryListTool,
    MemorySaveTool,
    MemorySearchTool,
)
from .read_url import ReadUrlTool
from .safe_code_runner import SafeCodeRunnerTool
from .source_compare import CompareSourcesTool
from .task_plan import CreateTaskPlanTool
from .web_search import WebSearchTool

log = logging.getLogger("jarvis.tools")


class ToolRegistry:
    def __init__(self, ctx: PermissionContext | None = None):
        self._tools: dict[str, Tool] = {}
        self.ctx = ctx or PermissionContext()
        self.trace: list[ToolCallTrace] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "permissions": [p.value for p in t.permissions],
                "input_schema": t.input_schema(),
            }
            for t in self._tools.values()
        ]

    def call(self, name: str, params: dict) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            res = ToolResult(ok=False, tool=name, error=f"Unknown tool '{name}'")
        else:
            res = tool.run(params, self.ctx)
        log.info("tool=%s ok=%s summary=%s", name, res.ok, res.summary or res.error)
        self.trace.append(
            ToolCallTrace(
                tool=name,
                input=_redact(params),
                ok=res.ok,
                summary=res.summary,
                error=res.error,
                duration_ms=round(res.duration_ms, 1),
            )
        )
        return res


def _redact(params: dict) -> dict:
    """Avoid logging large/binary fields."""
    out = {}
    for k, v in (params or {}).items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + "…"
        else:
            out[k] = v
    return out


def default_registry(ctx: PermissionContext | None = None) -> ToolRegistry:
    reg = ToolRegistry(ctx)
    for tool in (
        WebSearchTool(),
        ReadUrlTool(),
        CalculatorTool(),
        MemorySaveTool(),
        MemorySearchTool(),
        MemoryListTool(),
        MemoryDeleteTool(),
        LocalFileIngestTool(),
        LocalFileSearchTool(),
        CompareSourcesTool(),
        CreateTaskPlanTool(),
        SafeCodeRunnerTool(),
        DatetimeTool(),
        SystemHealthTool(),
    ):
        reg.register(tool)
    return reg
