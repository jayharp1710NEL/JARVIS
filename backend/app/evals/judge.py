"""Judge — transparent, deterministic scoring of a candidate answer.

Scoring is rule-based against each task's rubric so results are reproducible
and do not depend on a (paid) LLM judge. An optional model judge could be
added later, but the honest default is rule-based.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..agent.schemas import ChatResponse
from .rubrics import normalize_weights
from .tasks import EvalTask, Rubric


@dataclass
class Candidate:
    """Normalized view of either a full ChatResponse or a raw baseline string."""
    answer: str
    sources: list = field(default_factory=list)
    file_citations: list = field(default_factory=list)
    memory_used: list = field(default_factory=list)
    tool_trace: list = field(default_factory=list)  # list of dicts {tool, summary, ok}
    confidence: str = "medium"
    uncertainty: list = field(default_factory=list)

    @classmethod
    def from_response(cls, r: ChatResponse) -> "Candidate":
        return cls(
            answer=r.answer,
            sources=r.sources,
            file_citations=r.file_citations,
            memory_used=r.memory_used,
            tool_trace=[{"tool": t.tool, "summary": t.summary, "ok": t.ok} for t in r.tool_trace],
            confidence=r.confidence.value,
            uncertainty=r.uncertainty,
        )

    @classmethod
    def from_raw(cls, text: str) -> "Candidate":
        return cls(answer=text)


@dataclass
class Score:
    task_id: str
    category: str
    score: float          # 0..1 (fraction of max)
    max_score: float
    passed: bool
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def _kw_any(text: str, kws: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in kws)


def _kw_all(text: str, kws: list[str]) -> bool:
    t = text.lower()
    return all(k.lower() in t for k in kws)


def _tool_used(trace: list[dict], name: str) -> bool:
    return any(t.get("tool") == name and t.get("ok") for t in trace)


def _tool_summary_contains(trace: list[dict], needle: str) -> bool:
    return any(needle.lower() in (t.get("summary") or "").lower() for t in trace)


def score_candidate(task: EvalTask, cand: Candidate) -> Score:
    r: Rubric = task.rubric
    comps: dict[str, float] = {}
    reasons: list[str] = []

    if r.expect_keywords_any:
        ok = _kw_any(cand.answer, r.expect_keywords_any)
        comps["keywords_any"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append(f"missing any of {r.expect_keywords_any}")
    if r.expect_keywords_all:
        ok = _kw_all(cand.answer, r.expect_keywords_all)
        comps["keywords_all"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append(f"missing all of {r.expect_keywords_all}")
    if r.forbid_keywords:
        bad = [k for k in r.forbid_keywords if k.lower() in cand.answer.lower()]
        comps["forbid"] = 0.0 if bad else 1.0
        if bad:
            reasons.append(f"contains forbidden: {bad}")
    if r.require_sources:
        ok = len(cand.sources) > 0
        comps["sources"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("no sources cited")
    if r.require_file_citations:
        ok = len(cand.file_citations) > 0
        comps["citations"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("no file citations")
    if r.require_memory_used:
        ok = len(cand.memory_used) > 0
        comps["memory"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("did not use memory")
    if r.require_tool:
        ok = _tool_used(cand.tool_trace, r.require_tool)
        comps["tool"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append(f"did not use tool {r.require_tool}")
    if r.tool_result_contains:
        ok = _tool_summary_contains(cand.tool_trace, r.tool_result_contains) or \
            r.tool_result_contains.lower() in cand.answer.lower()
        comps["tool_result"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append(f"tool result missing '{r.tool_result_contains}'")
    if r.require_uncertainty:
        ok = len(cand.uncertainty) > 0
        comps["uncertainty"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("did not express uncertainty")
    if r.require_caution:
        ok = _kw_any(cand.answer, ["professional", "consult", "qualified", "not professional advice", "doctor", "expert"])
        comps["caution"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("no safety caution")
    if r.forbid_high_confidence:
        ok = cand.confidence != "high"
        comps["confidence"] = 1.0 if ok else 0.0
        if not ok:
            reasons.append("overconfident (high) given missing evidence")

    weights = normalize_weights(r.weights) if r.weights else {
        k: 1.0 / len(comps) for k in comps
    } if comps else {}
    total = sum(weights.get(k, 0.0) * v for k, v in comps.items()) if weights else 0.0
    # If rubric had components but no weights matched, average them.
    if comps and not weights:
        total = sum(comps.values()) / len(comps)

    passed = total >= 0.6
    return Score(
        task_id=task.id,
        category=task.category,
        score=round(total, 3),
        max_score=task.max_score,
        passed=passed,
        components=comps,
        reasons=reasons,
    )
