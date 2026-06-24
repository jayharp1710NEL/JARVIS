"""Deterministic in-process provider.

Used for: (a) the test suite, (b) the eval lab when no real model is
configured, and (c) a graceful offline fallback. It performs no network I/O.

It is intentionally simple but *honest*: it does not pretend to be smart. It
echoes the prompt context so tests can verify that sources/memory/files were
actually injected into the model input, and it can be scripted with canned
responses keyed by a substring of the latest user content.
"""
from __future__ import annotations

from typing import AsyncIterator, Callable, Optional

from ..agent.schemas import Message
from .base import GenSettings, HealthStatus, ModelProvider, extract_json


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(
        self,
        responder: Optional[Callable[[list[Message], GenSettings], str]] = None,
        model: str = "fake-1",
        json_responder: Optional[Callable[[list[Message]], object]] = None,
    ):
        self.model = model
        self.responder = responder
        self.json_responder = json_responder
        self.calls: list[list[Message]] = []
        self.scripted: dict[str, str] = {}

    def script(self, key: str, response: str) -> "FakeProvider":
        self.scripted[key] = response
        return self

    def _default_text(self, messages: list[Message]) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role.value == "user"),
            "",
        )
        for key, val in self.scripted.items():
            if key.lower() in last_user.lower():
                return val
        # Honest echo: surface that we are the offline fake model.
        return (
            "[offline fake-model response] "
            + last_user.strip()[:400]
        )

    def generate(self, messages: list[Message], settings: GenSettings) -> str:
        self.calls.append(list(messages))
        if self.responder:
            return self.responder(messages, settings)
        return self._default_text(messages)

    def generate_json(self, messages: list[Message], schema, settings: GenSettings):
        self.calls.append(list(messages))
        if self.json_responder:
            return self.json_responder(messages)
        text = self.responder(messages, settings) if self.responder else self._default_text(messages)
        try:
            return extract_json(text)
        except Exception:
            return {}

    async def stream(
        self, messages: list[Message], settings: GenSettings
    ) -> AsyncIterator[str]:
        text = self.generate(messages, settings)
        for token in text.split(" "):
            yield token + " "

    def list_models(self) -> list[str]:
        return [self.model]

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            ok=True,
            provider=self.name,
            detail="In-process fake provider (no network).",
            models=[self.model],
        )
