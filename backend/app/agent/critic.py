"""Critic — model-driven self-critique and revision (with safe fallbacks)."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.base import GenSettings, ModelProvider
from .executor import GatheredContext
from .prompts import CRITIQUE_PROMPT, REVISE_PROMPT
from .schemas import Message, Role
from .verifier import VerificationReport


@dataclass
class Critique:
    issues: list[str]
    needs_revision: bool
    severity: str = "low"


def critique(
    provider: ModelProvider,
    message: str,
    draft: str,
    ctx: GatheredContext,
    report: VerificationReport,
) -> Critique:
    issues: list[str] = []
    # Deterministic issues from verification first.
    if report.unsupported:
        issues.append(
            f"{len(report.unsupported)} statement(s) lack clear support in the "
            "evidence; hedge or cite them."
        )
    if report.grounded_ratio < 0.6 and ctx.has_evidence():
        issues.append("Overall groundedness is low relative to available evidence.")

    # Model critique (best-effort).
    try:
        evidence = ctx.evidence_block()[:6000] or "(no external evidence gathered)"
        prompt = CRITIQUE_PROMPT.format(message=message, evidence=evidence, draft=draft[:6000])
        data = provider.generate_json(
            [Message(role=Role.user, content=prompt)], None,
            GenSettings(temperature=0.0, max_tokens=400),
        )
        if isinstance(data, dict):
            for it in data.get("issues", []) or []:
                if isinstance(it, str) and it.strip():
                    issues.append(it.strip())
            severity = str(data.get("severity", "low"))
            needs = bool(data.get("needs_revision", False)) or bool(issues)
            return Critique(issues=issues[:8], needs_revision=needs, severity=severity)
    except Exception:
        pass

    return Critique(issues=issues[:8], needs_revision=bool(issues), severity="medium" if issues else "low")


def revise(
    provider: ModelProvider,
    message: str,
    draft: str,
    crit: Critique,
    ctx: GatheredContext,
) -> str:
    if not crit.needs_revision or not crit.issues:
        return draft
    try:
        evidence = ctx.evidence_block()[:6000] or "(no external evidence gathered)"
        prompt = REVISE_PROMPT.format(
            message=message,
            issues="\n".join(f"- {i}" for i in crit.issues),
            evidence=evidence,
            draft=draft,
        )
        improved = provider.generate(
            [Message(role=Role.user, content=prompt)],
            GenSettings(temperature=0.3, max_tokens=1200),
        )
        if improved and len(improved.strip()) > 20:
            return improved.strip()
    except Exception:
        pass
    return draft
