"""Scoring dimensions and labels shared by the judge and reports."""
from __future__ import annotations

DIMENSIONS = [
    "correctness",
    "completeness",
    "groundedness",
    "citation_quality",
    "uncertainty_honesty",
    "tool_use",
    "safety",
]


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}
