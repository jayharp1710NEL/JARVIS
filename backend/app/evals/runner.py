"""Eval runner — runs the benchmark, compares Jarvis vs baseline, reports.

Usage:
    python -m app.evals.runner run
    jarvis eval run

Uses the configured model provider when reachable; otherwise falls back to the
offline fake model and labels the report accordingly (so scores are never
misrepresented).
"""
from __future__ import annotations

import sys
import time

from ..agent.orchestrator import AgentOrchestrator
from ..agent.schemas import ChatRequest, Mode
from ..config import get_settings
from ..memory.db import init_engine
from ..memory.schemas import MemoryCreate, MemoryType
from ..memory.service import memory_service
from ..models.base import ModelProvider
from ..models.fake import FakeProvider
from ..models.router import build_provider
from ..rag.ingest import ingest_bytes
from ..web.search_providers import get_search_provider
from .baseline import raw_answer
from .judge import Candidate, score_candidate
from .reports import (
    EvalReport,
    TaskOutcome,
    detect_regressions,
    load_previous,
    save_report,
    suggest_improvements,
)
from .tasks import EvalTask, default_tasks


def _select_provider() -> tuple[ModelProvider, bool]:
    """Return (provider, is_offline_fake)."""
    settings = get_settings()
    try:
        prov = build_provider(settings.model_provider, settings)
        status = prov.health_check()
        if status.ok:
            return prov, False
    except Exception:
        pass
    return FakeProvider(), True


def _setup_task(task: EvalTask) -> list[str]:
    file_ids: list[str] = []
    for mem in task.seed_memory:
        memory_service.save(
            MemoryCreate(
                content=mem["content"],
                type=MemoryType(mem.get("type", "task_note")),
                tags=mem.get("tags", []),
                importance=0.8,
            )
        )
    if task.seed_file:
        res = ingest_bytes(task.seed_file["filename"], task.seed_file["content"].encode("utf-8"))
        file_ids.append(res.file_id)
    return file_ids


def run_evals() -> EvalReport:
    settings = get_settings()
    init_engine()
    provider, offline = _select_provider()

    try:
        sp = get_search_provider(settings)
        search_available, _ = sp.available()
    except Exception:
        search_available = False

    orchestrator = AgentOrchestrator(provider=provider)
    tasks = default_tasks()
    outcomes: list[TaskOutcome] = []

    for task in tasks:
        file_ids = _setup_task(task)
        req = ChatRequest(
            message=task.prompt,
            mode=Mode(task.mode),
            file_ids=file_ids,
            use_files=True if task.files_needed else None,
            use_memory=True if task.memory_needed else None,
            use_web=True if task.web_allowed else None,
        )
        # Jarvis (full agent)
        try:
            resp = orchestrator.run(req)
            jarvis_cand = Candidate.from_response(resp)
        except Exception as exc:  # noqa: BLE001
            jarvis_cand = Candidate.from_raw(f"[jarvis error: {exc}]")
        jscore = score_candidate(task, jarvis_cand)

        # Baseline (raw model, no tools)
        bscore = score_candidate(task, raw_answer(provider, task.prompt))

        outcomes.append(
            TaskOutcome(
                task_id=task.id,
                category=task.category,
                jarvis_score=jscore.score,
                baseline_score=bscore.score,
                delta=round(jscore.score - bscore.score, 3),
                passed=jscore.passed,
                web_allowed=task.web_allowed,
                reasons=jscore.reasons,
                baseline_reasons=bscore.reasons,
            )
        )

    n = len(outcomes) or 1
    jarvis_avg = round(sum(o.jarvis_score for o in outcomes) / n, 3)
    baseline_avg = round(sum(o.baseline_score for o in outcomes) / n, 3)
    pass_rate = round(sum(1 for o in outcomes if o.passed) / n, 3)

    notes = []
    if offline:
        notes.append(
            "Offline fake model in use — knowledge/coding/factual scores reflect "
            "the fake model, NOT the architecture. Run Ollama for real model scores."
        )
    if not search_available:
        notes.append(
            "No search provider reachable — web research / citation tasks score "
            "low honestly. Start SearxNG to enable them."
        )

    report = EvalReport(
        created_at=time.time(),
        provider=provider.name,
        model=getattr(provider, "model", "unknown"),
        offline_fake=offline,
        search_available=search_available,
        outcomes=outcomes,
        jarvis_avg=jarvis_avg,
        baseline_avg=baseline_avg,
        delta_avg=round(jarvis_avg - baseline_avg, 3),
        pass_rate=pass_rate,
        notes=notes,
    )
    save_report(report)
    return report


def print_report(report: EvalReport) -> None:
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="JARVIS-LOCAL Eval — Jarvis vs Baseline")
        table.add_column("Task")
        table.add_column("Category")
        table.add_column("Jarvis", justify="right")
        table.add_column("Baseline", justify="right")
        table.add_column("Δ", justify="right")
        table.add_column("Pass")
        for o in report.outcomes:
            delta_str = f"{o.delta:+.2f}"
            color = "green" if o.delta > 0 else ("red" if o.delta < 0 else "white")
            table.add_row(
                o.task_id, o.category, f"{o.jarvis_score:.2f}",
                f"{o.baseline_score:.2f}", f"[{color}]{delta_str}[/{color}]",
                "✅" if o.passed else "❌",
            )
        console.print(table)
        console.print(
            f"[bold]Jarvis avg:[/bold] {report.jarvis_avg:.2f}  "
            f"[bold]Baseline avg:[/bold] {report.baseline_avg:.2f}  "
            f"[bold]Δ:[/bold] {report.delta_avg:+.2f}  "
            f"[bold]Pass rate:[/bold] {report.pass_rate:.0%}"
        )
        prev = load_previous()
        regs = detect_regressions(report, prev)
        if regs:
            console.print("[red bold]Regressions:[/red bold] " + "; ".join(regs))
        for note in report.notes:
            console.print(f"[yellow]note:[/yellow] {note}")
        for tip in suggest_improvements(report):
            console.print(f"[cyan]suggest:[/cyan] {tip}")
    except Exception:  # pragma: no cover - rich optional
        print(f"Jarvis avg {report.jarvis_avg} vs Baseline {report.baseline_avg} "
              f"(Δ {report.delta_avg:+.2f}), pass rate {report.pass_rate:.0%}")
        for o in report.outcomes:
            print(f"  {o.task_id:14s} {o.category:26s} J={o.jarvis_score:.2f} "
                  f"B={o.baseline_score:.2f} Δ={o.delta:+.2f} {'PASS' if o.passed else 'FAIL'}")
        for note in report.notes:
            print("note:", note)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "run"
    if cmd != "run":
        print("usage: python -m app.evals.runner run")
        return 2
    report = run_evals()
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
