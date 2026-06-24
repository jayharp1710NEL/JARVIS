"""Minimal, defensive sandbox for the optional safe code runner.

This is intentionally conservative: code execution is DISABLED by default and
even when enabled it runs in a subprocess with a wall-clock timeout, no shell,
and a blocklist of obviously dangerous imports/patterns. This is *not* a
security boundary strong enough for hostile code — it is a guard rail for the
user's own snippets. The README states this clearly.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Patterns we refuse to run even when code execution is enabled.
_BLOCKED = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bsocket\b",
    r"\bshutil\.rmtree\b",
    r"\bos\.remove\b",
    r"\bos\.unlink\b",
    r"\bopen\([^)]*['\"]w",  # writing files
    r"\b__import__\b",
    r"\beval\(",
    r"\bexec\(",
    r"\brequests\b",
    r"\burllib\b",
    r"\bhttpx\b",
    r"\brm\s+-rf\b",
]
_BLOCKED_RE = [re.compile(p) for p in _BLOCKED]


@dataclass
class CodeResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    blocked_reason: str | None = None


def static_check(code: str) -> str | None:
    for rx in _BLOCKED_RE:
        if rx.search(code):
            return f"blocked pattern: {rx.pattern}"
    return None


def run_python(code: str, *, timeout: float = 5.0) -> CodeResult:
    """Run a small Python snippet in a subprocess with a timeout.

    Only stdlib math/data work is intended. Network/file/process operations
    are statically blocked.
    """
    reason = static_check(code)
    if reason:
        return CodeResult(False, "", "", -1, blocked_reason=reason)

    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script)],  # -I: isolated mode
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=td,
            )
        except subprocess.TimeoutExpired:
            return CodeResult(False, "", f"Timed out after {timeout}s", -1)
        return CodeResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout[:5000],
            stderr=proc.stderr[:5000],
            returncode=proc.returncode,
        )
