"""safe_code_runner tool — DISABLED by default; sandboxed when enabled.

Requires the ``code_exec`` permission, which is only granted when
``ALLOW_CODE_EXECUTION=true``. See ``security/sandbox.py`` for the (limited)
guard rails and the README for the explicit security caveat.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..security.permissions import Permission
from ..security.sandbox import run_python
from .base import Tool


class CodeRunInput(BaseModel):
    code: str = Field(..., description="Python snippet (stdlib math/data only)")
    timeout: float = Field(5.0, ge=0.1, le=15.0)


class SafeCodeRunnerTool(Tool):
    name = "safe_code_runner"
    description = (
        "Run a small Python snippet in an isolated subprocess (disabled unless "
        "code execution is explicitly enabled). No network/file/process access."
    )
    permissions = [Permission.code_exec]
    InputModel = CodeRunInput

    def execute(self, params: CodeRunInput):
        result = run_python(params.code, timeout=params.timeout)
        data = {
            "ok": result.ok,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "blocked_reason": result.blocked_reason,
        }
        if result.blocked_reason:
            raise RuntimeError(f"Refused to run: {result.blocked_reason}")
        summary = "ran ok" if result.ok else f"exited {result.returncode}"
        return data, summary
