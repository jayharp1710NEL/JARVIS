"""Planner — produces a short internal plan and web search queries."""
from __future__ import annotations

from ..models.base import GenSettings, ModelProvider
from ..tools.task_plan import heuristic_plan
from .prompts import QUERY_GEN_PROMPT
from .schemas import Message, Plan, PlanStep, Role


def make_plan(goal: str, max_steps: int = 6) -> Plan:
    steps = heuristic_plan(goal, max_steps)
    return Plan(steps=[PlanStep(id=i + 1, description=s) for i, s in enumerate(steps)])


def generate_queries(
    provider: ModelProvider,
    message: str,
    n: int,
    use_model: bool = True,
) -> list[str]:
    """Generate diverse search queries (model first, heuristic fallback)."""
    base = message.strip()
    heuristic = _heuristic_queries(base, n)
    if not use_model or n <= 1:
        return heuristic[:n]
    try:
        msgs = [Message(role=Role.user, content=QUERY_GEN_PROMPT.format(message=message, n=n))]
        data = provider.generate_json(msgs, None, GenSettings(temperature=0.3, max_tokens=300))
        queries = data.get("queries") if isinstance(data, dict) else None
        if isinstance(queries, list) and queries:
            cleaned = [str(q).strip() for q in queries if str(q).strip()]
            if cleaned:
                return cleaned[:n]
    except Exception:
        pass
    return heuristic[:n]


def _heuristic_queries(message: str, n: int) -> list[str]:
    base = message.strip().rstrip("?")
    variants = [
        base,
        f"{base} official documentation",
        f"{base} latest 2026",
        f"{base} criticism OR limitations OR problems",
        f"{base} explained in depth",
    ]
    # de-dup while preserving order
    seen: set[str] = set()
    out = []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out[:n]
