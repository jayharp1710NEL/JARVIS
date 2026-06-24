"""Composer — assembles the final ChatResponse with confidence & uncertainty.

The reasoning summary is generated from *what actually happened* (tools run,
sources read, claims verified) rather than from hidden chain-of-thought, so it
is honest and never leaks step-by-step reasoning.
"""
from __future__ import annotations

from ..tools.registry import ToolRegistry
from .executor import GatheredContext
from .schemas import (
    ChatResponse,
    Classification,
    Confidence,
    Mode,
    Source,
)
from .verifier import VerificationReport


def compute_confidence(
    cls: Classification,
    ctx: GatheredContext,
    report: VerificationReport | None,
    web_needed: bool,
    web_available: bool,
) -> Confidence:
    score = 0.6  # neutral prior
    if report is not None:
        score = 0.3 + 0.6 * report.grounded_ratio
    if ctx.sources:
        score += 0.1
        if any(s.source_type in ("official", "academic", "documentation") for s in ctx.sources):
            score += 0.05
    if ctx.file_chunks:
        score += 0.05
    if web_needed and not web_available:
        score -= 0.25
    if report and report.contradictions:
        score -= 0.1
    if cls.is_high_risk:
        score -= 0.1
    if not ctx.has_evidence() and cls.task_type.value in ("current_info", "research"):
        score -= 0.15

    if score >= 0.72:
        return Confidence.high
    if score >= 0.45:
        return Confidence.medium
    return Confidence.low


def build_uncertainty(
    ctx: GatheredContext,
    report: VerificationReport | None,
    web_needed: bool,
    web_available: bool,
) -> list[str]:
    items: list[str] = []
    if web_needed and not web_available:
        items.append("Web search was unavailable, so current information could not be verified.")
    if report:
        for u in report.unsupported[:4]:
            items.append(f"Not clearly supported by evidence: \"{u}\"")
        if report.contradictions:
            items.append("Sources disagree on at least one point; see claims.")
    for note in ctx.notes:
        if note not in items:
            items.append(note)
    # de-dup, cap
    seen, out = set(), []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out[:8]


def build_reasoning_summary(
    cls: Classification,
    ctx: GatheredContext,
    registry: ToolRegistry,
    report: VerificationReport | None,
) -> str:
    used_tools = sorted({t.tool for t in registry.trace if t.ok})
    parts = [f"Classified as **{cls.task_type.value}**."]
    if used_tools:
        parts.append("Tools used: " + ", ".join(used_tools) + ".")
    if ctx.sources:
        kinds = {}
        for s in ctx.sources:
            kinds[s.source_type] = kinds.get(s.source_type, 0) + 1
        kind_str = ", ".join(f"{v} {k}" for k, v in kinds.items())
        parts.append(f"Read {len(ctx.read_texts)} of {len(ctx.sources)} web sources ({kind_str}).")
    if ctx.file_chunks:
        parts.append(f"Retrieved {len(ctx.file_chunks)} excerpt(s) from local files.")
    if ctx.memory_used:
        parts.append(f"Recalled {len(ctx.memory_used)} memory item(s).")
    if ctx.math_context:
        parts.append("Verified arithmetic with the calculator.")
    if report is not None:
        parts.append(
            f"Self-verified claims: {int(report.grounded_ratio * 100)}% grounded in evidence."
        )
    return " ".join(parts)


def suggest_next_action(cls: Classification, ctx: GatheredContext, web_available: bool) -> str:
    if cls.task_type.value in ("current_info", "research") and not web_available:
        return "Start a local SearxNG instance (or set a search API key) to enable verified web research."
    if cls.task_type.value == "research" and len(ctx.sources) < 3:
        return "Ask for deeper research to pull and compare more primary sources."
    if cls.task_type.value == "coding":
        return "Ask me to write tests for this, or to run the snippet via the safe code runner."
    if cls.task_type.value == "document_qa" and not ctx.file_chunks:
        return "Ingest the relevant document first with `jarvis ingest <file>`."
    if cls.is_high_risk:
        return "Consult a qualified professional before acting on this."
    return ""


def high_risk_caution(cls: Classification) -> str:
    if not cls.is_high_risk:
        return ""
    return (
        "\n\n> ⚠ This touches a medical/legal/financial topic. This is general "
        "information, not professional advice — please consult a qualified expert."
    )


def assemble(
    *,
    answer: str,
    mode: Mode,
    cls: Classification,
    ctx: GatheredContext,
    registry: ToolRegistry,
    report: VerificationReport | None,
    web_needed: bool,
    web_available: bool,
    warnings: list[str],
) -> ChatResponse:
    confidence = compute_confidence(cls, ctx, report, web_needed, web_available)
    answer = answer + high_risk_caution(cls)
    sources: list[Source] = ctx.sources
    return ChatResponse(
        answer=answer.strip(),
        mode=mode,
        sources=sources,
        file_citations=ctx.file_citations,
        memory_used=ctx.memory_used,
        tool_trace=registry.trace,
        claims=(report.claims if report else []),
        confidence=confidence,
        uncertainty=build_uncertainty(ctx, report, web_needed, web_available),
        reasoning_summary=build_reasoning_summary(cls, ctx, registry, report),
        next_best_action=suggest_next_action(cls, ctx, web_available),
        warnings=warnings,
    )
