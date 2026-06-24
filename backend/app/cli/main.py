"""JARVIS-LOCAL command line interface (Typer + Rich)."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..agent.orchestrator import AgentOrchestrator
from ..agent.schemas import ChatRequest, Mode
from ..config import get_settings
from ..memory.db import init_engine

app = typer.Typer(
    add_completion=False,
    help="JARVIS-LOCAL — a local-first, private, tool-using AI agent.",
    no_args_is_help=True,
)
memory_app = typer.Typer(help="Inspect and manage local memory.")
files_app = typer.Typer(help="Index and search local files.")
app.add_typer(memory_app, name="memory")
app.add_typer(files_app, name="files")

console = Console()


def _render(resp) -> None:
    console.print(Panel(Markdown(resp.answer), title=f"JARVIS · {resp.mode.value}", border_style="cyan"))
    badge = {"high": "green", "medium": "yellow", "low": "red"}[resp.confidence.value]
    console.print(f"Confidence: [{badge}]{resp.confidence.value.upper()}[/{badge}]")
    if resp.reasoning_summary:
        console.print(f"[dim]Reasoning:[/dim] {resp.reasoning_summary}")
    if resp.sources:
        t = Table(title="Sources", show_lines=False)
        t.add_column("#"); t.add_column("Title"); t.add_column("Domain"); t.add_column("Type")
        for i, s in enumerate(resp.sources, 1):
            t.add_row(str(i), s.title[:50], s.domain, s.source_type)
        console.print(t)
    if resp.file_citations:
        console.print("[dim]Files:[/dim] " + ", ".join(
            f"{c.filename}" + (f" p.{c.page}" if c.page else "") for c in resp.file_citations))
    if resp.memory_used:
        console.print(f"[dim]Memory used:[/dim] {len(resp.memory_used)} item(s)")
    if resp.uncertainty:
        console.print("[yellow]Uncertainty:[/yellow]")
        for u in resp.uncertainty:
            console.print(f"  • {u}")
    if resp.next_best_action:
        console.print(f"[cyan]Next:[/cyan] {resp.next_best_action}")
    for w in resp.warnings:
        console.print(f"[red]{w}[/red]")


def _ask(message: str, mode: Mode, privacy: bool = False, web: bool | None = None) -> None:
    init_engine()
    orch = AgentOrchestrator()
    with console.status("[cyan]thinking…[/cyan]"):
        resp = orch.run(ChatRequest(message=message, mode=mode, local_privacy=privacy, use_web=web))
    _render(resp)


@app.command()
def ask(question: str = typer.Argument(..., help="Your question")):
    """Ask a quick question (fast mode)."""
    _ask(question, Mode.fast)


@app.command()
def research(topic: str = typer.Argument(..., help="Topic to research")):
    """Research a topic with web sources and citations."""
    _ask(topic, Mode.research, web=True)


@app.command()
def deep(question: str = typer.Argument(..., help="A hard question")):
    """Deep-think mode: planning, verification, self-critique."""
    _ask(question, Mode.deep)


@app.command()
def truth(claim: str = typer.Argument(..., help="A claim or question")):
    """Truth mode: separates facts, evidence, assumptions, speculation, unknowns."""
    _ask(claim, Mode.truth)


@app.command()
def chat():
    """Interactive chat session."""
    init_engine()
    orch = AgentOrchestrator()
    history: list = []
    console.print("[cyan]JARVIS-LOCAL chat[/cyan] — type 'exit' to quit.")
    while True:
        try:
            msg = console.input("[bold green]you ›[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            break
        if msg.strip().lower() in ("exit", "quit"):
            break
        if not msg.strip():
            continue
        with console.status("[cyan]thinking…[/cyan]"):
            resp = orch.run(ChatRequest(message=msg, history=history, mode=Mode.fast))
        _render(resp)
        from ..agent.schemas import Message, Role
        history.append(Message(role=Role.user, content=msg))
        history.append(Message(role=Role.assistant, content=resp.answer))


@app.command()
def models():
    """List available models from the configured provider."""
    from ..models.router import build_provider
    settings = get_settings()
    try:
        provider = build_provider(settings.model_provider, settings)
        status = provider.health_check()
        console.print(f"Provider: [bold]{settings.model_provider}[/bold] — {status.detail}")
        for m in status.models or provider.list_models():
            console.print(f"  • {m}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]{exc}[/red]")


@app.command()
def settings():
    """Show effective configuration."""
    s = get_settings()
    t = Table(title="Settings")
    t.add_column("Key"); t.add_column("Value")
    for k, v in {
        "model_provider": s.model_provider, "ollama_model": s.ollama_model,
        "search_provider": s.search_provider, "searxng_url": s.searxng_url,
        "embedding_provider": s.embedding_provider, "vector_store": s.vector_store,
        "local_privacy_mode": s.local_privacy_mode, "cloud_enabled": s.enable_cloud_mode,
        "code_execution": s.allow_code_execution, "data_dir": str(s.data_dir),
    }.items():
        t.add_row(k, str(v))
    console.print(t)


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI backend with uvicorn."""
    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


@app.command()
def ingest(path: str = typer.Argument(..., help="Path to a file to index")):
    """Ingest a local file into the RAG index."""
    init_engine()
    from ..rag.ingest import ingest_path
    from ..rag.loaders import UnsupportedFileType
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found: {p}[/red]")
        raise typer.Exit(1)
    try:
        res = ingest_path(p)
    except UnsupportedFileType as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Indexed[/green] {res.filename} → {res.num_chunks} chunks (id={res.file_id})")
    if res.injection_flagged:
        console.print("[yellow]⚠ This file contained instruction-like text; it will be treated as data.[/yellow]")


@files_app.command("search")
def files_search(query: str, top_k: int = 5):
    """Search indexed files."""
    init_engine()
    from ..rag.retrieval import retrieve
    chunks = retrieve(query, top_k)
    if not chunks:
        console.print("[yellow]No matches. Ingest files first with `jarvis ingest <file>`.[/yellow]")
        return
    for c in chunks:
        loc = f"p.{c.page}" if c.page else c.chunk_id
        console.print(Panel(c.text[:400], title=f"{c.filename} ({loc}) score={c.score:.2f}"))


@files_app.command("list")
def files_list():
    """List indexed files."""
    init_engine()
    from ..rag.ingest import list_indexed_files
    rows = list_indexed_files()
    if not rows:
        console.print("[yellow]No indexed files.[/yellow]")
        return
    t = Table(title="Indexed files")
    t.add_column("id"); t.add_column("filename"); t.add_column("type"); t.add_column("chunks")
    for r in rows:
        t.add_row(r["id"], r["filename"], r["file_type"], str(r["num_chunks"]))
    console.print(t)


@memory_app.command("list")
def memory_list(limit: int = 50):
    """List stored memories."""
    init_engine()
    from ..memory.service import memory_service
    items = memory_service.list(limit)
    if not items:
        console.print("[yellow]No memories yet.[/yellow]")
        return
    t = Table(title="Memory")
    t.add_column("id"); t.add_column("type"); t.add_column("content"); t.add_column("imp")
    for m in items:
        t.add_row(m.id, m.type.value, m.content[:60], f"{m.importance:.1f}")
    console.print(t)


@memory_app.command("save")
def memory_save(content: str, type: str = "task_note", tags: str = ""):
    """Save a memory."""
    init_engine()
    from ..memory.schemas import MemoryCreate, MemoryType
    from ..memory.service import memory_service
    item = memory_service.save(MemoryCreate(
        content=content, type=MemoryType(type),
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        user_confirmed=True,
    ))
    console.print(f"[green]Saved[/green] {item.id}")


@memory_app.command("delete")
def memory_delete(mem_id: str):
    """Delete a memory by id."""
    init_engine()
    from ..memory.service import memory_service
    ok = memory_service.delete(mem_id)
    console.print("[green]deleted[/green]" if ok else "[red]not found[/red]")


# `jarvis eval run`
eval_app = typer.Typer(help="Run benchmarks.")
app.add_typer(eval_app, name="eval")


@eval_app.command("run")
def eval_run():
    """Run the eval suite (Jarvis vs baseline)."""
    init_engine()
    from ..evals.runner import print_report, run_evals
    with console.status("[cyan]running evals…[/cyan]"):
        report = run_evals()
    print_report(report)


if __name__ == "__main__":
    app()
