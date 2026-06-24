"""Baseline: raw local-model answer with NO tools/memory/web/verification.

Comparing this against the full Jarvis agent is how we measure whether the
agent layer actually adds practical value — honestly, per task.
"""
from __future__ import annotations

from ..models.base import GenSettings, ModelProvider
from ..agent.schemas import Message, Role
from .judge import Candidate

_BASELINE_SYSTEM = (
    "You are a helpful assistant. Answer the user's question directly."
)


def raw_answer(provider: ModelProvider, prompt: str) -> Candidate:
    msgs = [
        Message(role=Role.system, content=_BASELINE_SYSTEM),
        Message(role=Role.user, content=prompt),
    ]
    try:
        text = provider.generate(msgs, GenSettings(temperature=0.7, max_tokens=600))
    except Exception as exc:  # noqa: BLE001
        text = f"[baseline model error: {exc}]"
    return Candidate.from_raw(text)
