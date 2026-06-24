"""File ingestion pipeline: load -> chunk -> embed -> store + index metadata."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings
from ..memory.db import IndexedFileRow, get_session
from ..security.prompt_injection import scan
from .chunking import chunk_text
from .embeddings import get_embedder
from .loaders import LoadedDoc, load_bytes, load_path
from .vector_store import VectorRecord, get_vector_store


@dataclass
class IngestResult:
    file_id: str
    filename: str
    file_type: str
    num_chunks: int
    bytes: int
    injection_flagged: bool = False


def _index_doc(doc: LoadedDoc) -> IngestResult:
    settings = get_settings()
    embedder = get_embedder(settings)
    store = get_vector_store(settings)
    file_id = uuid.uuid4().hex[:12]

    records: list[VectorRecord] = []
    texts: list[str] = []
    injection_flagged = False

    for page in doc.pages:
        if scan(page.text).suspicious:
            injection_flagged = True
        for ch in chunk_text(page.text, settings.chunk_size, settings.chunk_overlap, page.page):
            rec = VectorRecord(
                id=f"{file_id}:{len(records)}",
                file_id=file_id,
                filename=doc.filename,
                text=ch.text,
                page=ch.page,
                chunk_index=ch.index,
            )
            records.append(rec)
            texts.append(ch.text)

    if records:
        vectors = embedder.embed(texts)
        store.add(vectors, records)

    with get_session() as s:
        s.add(
            IndexedFileRow(
                id=file_id,
                filename=doc.filename,
                file_type=doc.file_type,
                num_chunks=len(records),
                bytes=doc.bytes,
            )
        )
        s.commit()

    return IngestResult(
        file_id=file_id,
        filename=doc.filename,
        file_type=doc.file_type,
        num_chunks=len(records),
        bytes=doc.bytes,
        injection_flagged=injection_flagged,
    )


def ingest_path(path: str | Path) -> IngestResult:
    return _index_doc(load_path(path))


def ingest_bytes(filename: str, data: bytes) -> IngestResult:
    return _index_doc(load_bytes(filename, data))


def list_indexed_files() -> list[dict]:
    with get_session() as s:
        rows = s.query(IndexedFileRow).order_by(IndexedFileRow.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "file_type": r.file_type,
                "num_chunks": r.num_chunks,
                "bytes": r.bytes,
                "created_at": r.created_at,
            }
            for r in rows
        ]


def delete_indexed_file(file_id: str) -> bool:
    store = get_vector_store()
    removed = store.delete_file(file_id)
    with get_session() as s:
        row = s.get(IndexedFileRow, file_id)
        if row:
            s.delete(row)
            s.commit()
    return removed > 0 or False
