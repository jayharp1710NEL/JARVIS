"""Retrieval over the local file index, producing chunks + file citations."""
from __future__ import annotations

from dataclasses import dataclass

from ..agent.schemas import FileCitation
from ..config import get_settings
from .embeddings import get_embedder
from .vector_store import SearchHit, get_vector_store


@dataclass
class RetrievedChunk:
    text: str
    filename: str
    file_id: str
    chunk_id: str
    page: int | None
    score: float


def retrieve(query: str, top_k: int | None = None, file_ids: list[str] | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    top_k = top_k or settings.rag_top_k
    embedder = get_embedder(settings)
    store = get_vector_store(settings)
    qvec = embedder.embed_one(query)
    # Over-fetch then filter by file when a subset is requested.
    hits: list[SearchHit] = store.search(qvec, top_k * 3 if file_ids else top_k)
    out: list[RetrievedChunk] = []
    for h in hits:
        if file_ids and h.record.file_id not in file_ids:
            continue
        out.append(
            RetrievedChunk(
                text=h.record.text,
                filename=h.record.filename,
                file_id=h.record.file_id,
                chunk_id=h.record.id,
                page=h.record.page,
                score=round(h.score, 4),
            )
        )
        if len(out) >= top_k:
            break
    return out


def to_citations(chunks: list[RetrievedChunk]) -> list[FileCitation]:
    cites = []
    for c in chunks:
        excerpt = c.text.strip().replace("\n", " ")
        cites.append(
            FileCitation(
                filename=c.filename,
                page=c.page,
                chunk_id=c.chunk_id,
                excerpt=excerpt[:300],
                score=c.score,
            )
        )
    return cites
