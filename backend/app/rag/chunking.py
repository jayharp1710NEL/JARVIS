"""Text chunking with overlap, preserving rough source offsets/pages."""
from __future__ import annotations

import re
from dataclasses import dataclass

_PARA_SPLIT = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    text: str
    index: int
    page: int | None = None
    start_char: int = 0


def _split_long(text: str, size: int) -> list[str]:
    """Split a too-long paragraph on sentence boundaries, then hard-wrap."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    buf = ""
    for sent in sentences:
        if len(buf) + len(sent) + 1 <= size:
            buf = (buf + " " + sent).strip()
        else:
            if buf:
                out.append(buf)
            if len(sent) > size:
                for i in range(0, len(sent), size):
                    out.append(sent[i : i + size])
                buf = ""
            else:
                buf = sent
    if buf:
        out.append(buf)
    return out


def chunk_text(
    text: str,
    chunk_size: int = 900,
    overlap: int = 150,
    page: int | None = None,
) -> list[Chunk]:
    """Greedy paragraph-packing chunker with character overlap.

    Keeps paragraphs intact when possible; overlaps the tail of one chunk into
    the next so retrieval doesn't lose context at boundaries.
    """
    text = (text or "").strip()
    if not text:
        return []

    pieces: list[str] = []
    for para in _PARA_SPLIT.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) > chunk_size:
            pieces.extend(_split_long(para, chunk_size))
        else:
            pieces.append(para)

    chunks: list[Chunk] = []
    buf = ""
    cursor = 0
    for piece in pieces:
        if buf and len(buf) + len(piece) + 2 > chunk_size:
            chunks.append(Chunk(text=buf, index=len(chunks), page=page, start_char=cursor))
            tail = buf[-overlap:] if overlap > 0 else ""
            cursor += max(0, len(buf) - len(tail))
            buf = (tail + "\n\n" + piece).strip()
        else:
            buf = (buf + "\n\n" + piece).strip() if buf else piece
    if buf:
        chunks.append(Chunk(text=buf, index=len(chunks), page=page, start_char=cursor))
    return chunks
