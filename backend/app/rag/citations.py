"""Helpers to render file citations into the context block and final answer."""
from __future__ import annotations

from ..agent.schemas import FileCitation
from .retrieval import RetrievedChunk


def build_file_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a labeled, data-only context block."""
    if not chunks:
        return ""
    lines = ["Relevant excerpts from your local files (cite as [F#]):"]
    for i, c in enumerate(chunks, start=1):
        loc = f"p.{c.page}" if c.page else f"chunk {c.chunk_id}"
        lines.append(f"[F{i}] ({c.filename}, {loc})\n{c.text.strip()}")
    return "\n\n".join(lines)


def format_citation_label(c: FileCitation, index: int) -> str:
    loc = f", p.{c.page}" if c.page else ""
    return f"[F{index}] {c.filename}{loc}"
