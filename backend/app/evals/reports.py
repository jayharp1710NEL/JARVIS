"""Eval report persistence, comparison and rendering."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import get_settings
from .judge import Score


@dataclass
class TaskOutcome:
    task_id: str
    category: str
    jarvis_score: float
    baseline_score: float
    delta: float
    passed: bool
    web_allowed: bool
    reasons: list[str] = field(default_factory=list)
    baseline_reasons: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    created_at: float
    provider: str
    model: str
    offline_fake: bool
    search_available: bool
    outcomes: list[TaskOutcome]
    jarvis_avg: float
    baseline_avg: float
    delta_avg: float
    pass_rate: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def reports_dir() -> Path:
    d = get_settings().eval_reports_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_report(report: EvalReport) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime(report.created_at))
    path = reports_dir() / f"eval-{ts}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2))
    latest = reports_dir() / "latest.json"
    latest.write_text(json.dumps(report.to_dict(), indent=2))
    return path


def load_previous(exclude_latest: bool = True) -> EvalReport | None:
    d = reports_dir()
    files = sorted(d.glob("eval-*.json"))
    if not files:
        return None
    # the most recent file is the run we just saved; take the one before it
    target = files[-2] if (exclude_latest and len(files) >= 2) else files[-1]
    try:
        data = json.loads(target.read_text())
        data["outcomes"] = [TaskOutcome(**o) for o in data["outcomes"]]
        return EvalReport(**data)
    except Exception:
        return None


def detect_regressions(current: EvalReport, previous: EvalReport | None) -> list[str]:
    if not previous:
        return []
    prev_map = {o.task_id: o.jarvis_score for o in previous.outcomes}
    regs = []
    for o in current.outcomes:
        old = prev_map.get(o.task_id)
        if old is not None and o.jarvis_score + 1e-6 < old - 0.05:
            regs.append(f"{o.task_id}: {old:.2f} -> {o.jarvis_score:.2f}")
    return regs


def suggest_improvements(report: EvalReport) -> list[str]:
    tips: list[str] = []
    by_cat: dict[str, list[float]] = {}
    for o in report.outcomes:
        by_cat.setdefault(o.category, []).append(o.jarvis_score)
    for cat, scores in by_cat.items():
        avg = sum(scores) / len(scores)
        if avg < 0.6:
            if "web" in cat or "citation" in cat or "research" in cat or "comparison" in cat:
                if not report.search_available:
                    tips.append(
                        f"[{cat}] low because no search provider is reachable — "
                        "start SearxNG or set a search API key to enable web research."
                    )
                else:
                    tips.append(f"[{cat}] low — improve query generation / source ranking.")
            elif "coding" in cat or "factual" in cat:
                if report.offline_fake:
                    tips.append(
                        f"[{cat}] low because the offline fake model is in use — "
                        "run Ollama with a capable model for knowledge/coding tasks."
                    )
                else:
                    tips.append(f"[{cat}] low — consider a stronger local model or better prompts.")
            else:
                tips.append(f"[{cat}] low — review the {cat} pipeline stage.")
    return tips
