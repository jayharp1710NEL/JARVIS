"""Request router / classifier.

Combines a model classification (when available) with deterministic heuristics.
Heuristics can *force-enable* context needs so the system is robust even when
the local model returns junk JSON. The result drives which tools run.
"""
from __future__ import annotations

import re

from ..models.base import GenSettings, ModelProvider
from .modes import ModeConfig
from .prompts import CLASSIFY_PROMPT
from .schemas import Classification, Message, Role, TaskType

_URL_RE = re.compile(r"https?://[^\s]+")
_MATH_RE = re.compile(r"[0-9]\s*[\+\-\*/\^%]\s*[0-9(]|\bsqrt\b|\bfactorial\b|\bintegral\b|\d+%\s+of\b")
_CODE_HINTS = ("code", "function", "bug", "python", "javascript", "typescript",
               "java", "c++", "rust", "golang", "compile", "stack trace",
               "regex", "api", "refactor", "implement", "class ", "def ")
_CURRENT_HINTS = ("today", "latest", "current", "right now", "this year",
                  "2024", "2025", "2026", "news", "recent", "stock", "price",
                  "release", "version", "weather", "who won", "score")
_RESEARCH_HINTS = ("research", "compare", "sources", "evidence", "study",
                   "according to", "cite", "papers", "literature")
_MEMORY_HINTS = ("remember", "i told you", "my preference", "you know that",
                 "recall", "my name is", "save this", "note that i")
_HIGH_RISK_HINTS = ("diagnos", "symptom", "medication", "dosage", "lawsuit",
                    "legal advice", "contract", "tax", "invest", "lawyer",
                    "medical", "prescription", "sue ")
_PLANNING_HINTS = ("plan", "roadmap", "step by step", "schedule", "organize",
                   "break down", "milestones")
_CREATIVE_HINTS = ("write a poem", "story", "lyrics", "fiction", "creative",
                   "screenplay", "haiku")


def heuristic_classify(message: str, has_files: bool) -> Classification:
    m = message.lower()
    needs_url = bool(_URL_RE.search(message))
    needs_math = bool(_MATH_RE.search(m))
    needs_web = any(h in m for h in _CURRENT_HINTS) or any(h in m for h in _RESEARCH_HINTS)
    needs_memory = any(h in m for h in _MEMORY_HINTS)
    is_high_risk = any(h in m for h in _HIGH_RISK_HINTS)

    if has_files:
        task = TaskType.document_qa
    elif any(h in m for h in _CODE_HINTS):
        task = TaskType.coding
    elif needs_math:
        task = TaskType.math
    elif any(h in m for h in _RESEARCH_HINTS):
        task = TaskType.research
    elif any(h in m for h in _CURRENT_HINTS):
        task = TaskType.current_info
    elif needs_memory:
        task = TaskType.memory_qa
    elif any(h in m for h in _PLANNING_HINTS):
        task = TaskType.planning
    elif any(h in m for h in _CREATIVE_HINTS):
        task = TaskType.creative
    elif is_high_risk:
        task = TaskType.high_risk
    elif len(message.split()) <= 4 and "?" not in message:
        task = TaskType.casual
    else:
        task = TaskType.factual

    return Classification(
        task_type=task,
        needs_web=needs_web,
        needs_files=has_files,
        needs_memory=needs_memory,
        needs_math=needs_math,
        needs_url_read=needs_url,
        is_high_risk=is_high_risk,
        rationale="heuristic",
    )


def _merge(model_c: Classification | None, heur: Classification) -> Classification:
    if model_c is None:
        return heur
    # Heuristics can only ADD needs (they are precision-oriented signals).
    return Classification(
        task_type=model_c.task_type,
        needs_web=model_c.needs_web or heur.needs_web,
        needs_files=model_c.needs_files or heur.needs_files,
        needs_memory=model_c.needs_memory or heur.needs_memory,
        needs_math=model_c.needs_math or heur.needs_math,
        needs_url_read=model_c.needs_url_read or heur.needs_url_read,
        is_high_risk=model_c.is_high_risk or heur.is_high_risk,
        rationale=(model_c.rationale or "model") + "+heuristic",
    )


def classify(
    provider: ModelProvider,
    message: str,
    has_files: bool,
    use_model: bool = True,
) -> Classification:
    heur = heuristic_classify(message, has_files)
    if not use_model:
        return heur
    try:
        msgs = [Message(role=Role.user, content=CLASSIFY_PROMPT.format(message=message))]
        data = provider.generate_json(msgs, None, GenSettings(temperature=0.0, max_tokens=300))
        if isinstance(data, dict) and data.get("task_type"):
            try:
                model_c = Classification(
                    task_type=TaskType(data.get("task_type", heur.task_type.value)),
                    needs_web=bool(data.get("needs_web", False)),
                    needs_files=bool(data.get("needs_files", False)),
                    needs_memory=bool(data.get("needs_memory", False)),
                    needs_math=bool(data.get("needs_math", False)),
                    needs_url_read=bool(data.get("needs_url_read", False)),
                    is_high_risk=bool(data.get("is_high_risk", False)),
                    rationale=str(data.get("rationale", "model"))[:200],
                )
                return _merge(model_c, heur)
            except ValueError:
                return heur
    except Exception:
        pass
    return heur
