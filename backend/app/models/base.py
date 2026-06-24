"""Model provider abstraction.

Every provider implements the same small interface so models are fully
swappable. Providers must fail loudly and clearly (never silently) so users
get actionable setup errors instead of cryptic stack traces.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterable, Optional

from ..agent.schemas import Message


class ModelError(RuntimeError):
    """Raised for provider failures with a user-actionable message."""


@dataclass
class GenSettings:
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1024
    stop: Optional[list[str]] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    ok: bool
    provider: str
    detail: str
    models: list[str] = field(default_factory=list)


def messages_to_dicts(messages: Iterable[Message] | Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if isinstance(m, Message):
            out.append(m.to_provider())
        elif isinstance(m, dict):
            out.append({"role": m["role"], "content": m["content"]})
        else:  # pragma: no cover - defensive
            raise TypeError(f"Unsupported message type: {type(m)}")
    return out


def extract_json(text: str) -> Any:
    """Best-effort extraction of a JSON object from a model response.

    Local models frequently wrap JSON in prose or code fences. We try, in
    order: direct parse, fenced block, first balanced object/array.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass

    # find first balanced {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
    raise ValueError("No JSON object could be parsed from model output")


class ModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, messages: list[Message], settings: GenSettings) -> str:
        ...

    @abstractmethod
    async def stream(
        self, messages: list[Message], settings: GenSettings
    ) -> AsyncIterator[str]:
        ...

    def generate_json(
        self, messages: list[Message], schema: dict | None, settings: GenSettings
    ) -> Any:
        """Generate and parse JSON. Default: prompt for JSON then parse.

        Providers with native JSON mode may override.
        """
        raw = self.generate(messages, settings)
        return extract_json(raw)

    @abstractmethod
    def health_check(self) -> HealthStatus:
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        ...

    def estimate_tokens(self, text: str) -> int:
        """Rough heuristic (~4 chars/token). Good enough for budgeting."""
        return max(1, len(text) // 4)
