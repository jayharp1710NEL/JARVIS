"""compare_sources tool — heuristic agreement/contradiction detection.

Given short claim statements (optionally tagged with a source id), it clusters
similar claims and flags likely contradictions using token overlap plus
negation/antonym signals. This is a transparent, dependency-free triangulation
aid; the model can refine it, but this gives a deterministic baseline.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .base import Tool

_WORD = re.compile(r"[a-z0-9]+")
_NEG = {"not", "no", "never", "without", "cannot", "isn't", "aren't", "doesn't",
        "don't", "won't", "false", "incorrect", "untrue", "fails", "unable"}
_ANTONYMS = [
    ({"increase", "rise", "higher", "more", "grew", "up"},
     {"decrease", "fall", "lower", "less", "fell", "down"}),
    ({"safe", "secure"}, {"unsafe", "insecure", "vulnerable"}),
    ({"true", "correct", "valid"}, {"false", "incorrect", "invalid"}),
    ({"supported", "available"}, {"unsupported", "unavailable", "deprecated"}),
]


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _similar(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _contradicts(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    base = (ta - _NEG) & (tb - _NEG)
    if len(base) < 2:
        return False
    neg_a = bool(ta & _NEG)
    neg_b = bool(tb & _NEG)
    if neg_a != neg_b and _similar(ta - _NEG, tb - _NEG) > 0.4:
        return True
    for left, right in _ANTONYMS:
        if (ta & left and tb & right) or (ta & right and tb & left):
            if _similar(ta - left - right, tb - left - right) > 0.25:
                return True
    return False


class ClaimItem(BaseModel):
    source_id: str = "?"
    text: str


class CompareInput(BaseModel):
    claims: list[ClaimItem] = Field(..., description="Claims to compare across sources")
    similarity_threshold: float = 0.45


def compare_claims(claims: list[ClaimItem], threshold: float = 0.45) -> dict:
    n = len(claims)
    toks = [_tokens(c.text) for c in claims]
    agreements: list[dict] = []
    contradictions: list[dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            if claims[i].source_id == claims[j].source_id:
                continue
            sim = _similar(toks[i], toks[j])
            if _contradicts(claims[i].text, claims[j].text):
                contradictions.append({
                    "a": claims[i].model_dump(), "b": claims[j].model_dump(),
                    "similarity": round(sim, 3),
                })
            elif sim >= threshold:
                agreements.append({
                    "a": claims[i].model_dump(), "b": claims[j].model_dump(),
                    "similarity": round(sim, 3),
                })
    return {
        "num_claims": n,
        "agreements": agreements,
        "contradictions": contradictions,
        "has_conflict": bool(contradictions),
    }


class CompareSourcesTool(Tool):
    name = "compare_sources"
    description = "Compare claims across sources to find agreement and contradictions."
    InputModel = CompareInput

    def execute(self, params: CompareInput):
        result = compare_claims(params.claims, params.similarity_threshold)
        summary = (
            f"{len(result['agreements'])} agreements, "
            f"{len(result['contradictions'])} contradictions"
        )
        return result, summary
