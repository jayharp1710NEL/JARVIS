"""Local vector store.

Default implementation is a pure-numpy cosine-similarity store persisted to
disk (``vectors.npy`` + ``meta.json``). Zero external dependencies, fully
local, easy to inspect, and good for the small/medium corpora a personal
assistant indexes. A ChromaDB-backed store can be swapped in via config.
"""
from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from ..config import Settings, get_settings


@dataclass
class VectorRecord:
    id: str
    file_id: str
    filename: str
    text: str
    page: Optional[int] = None
    chunk_index: int = 0
    meta: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    record: VectorRecord
    score: float


class VectorStore(ABC):
    @abstractmethod
    def add(self, vectors: np.ndarray, records: list[VectorRecord]) -> None: ...
    @abstractmethod
    def search(self, query_vec: np.ndarray, top_k: int) -> list[SearchHit]: ...
    @abstractmethod
    def delete_file(self, file_id: str) -> int: ...
    @abstractmethod
    def list_files(self) -> dict[str, int]: ...
    @abstractmethod
    def clear(self) -> None: ...
    @abstractmethod
    def count(self) -> int: ...


class NumpyVectorStore(VectorStore):
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.vec_path = self.dir / "vectors.npy"
        self.meta_path = self.dir / "meta.json"
        self._lock = threading.Lock()
        self._vectors: Optional[np.ndarray] = None
        self._records: list[VectorRecord] = []
        self._load()

    def _load(self) -> None:
        if self.vec_path.exists() and self.meta_path.exists():
            try:
                self._vectors = np.load(self.vec_path)
                raw = json.loads(self.meta_path.read_text())
                self._records = [VectorRecord(**r) for r in raw]
            except Exception:
                self._vectors, self._records = None, []
        else:
            self._vectors, self._records = None, []

    def _persist(self) -> None:
        if self._vectors is None:
            # write empties
            np.save(self.vec_path, np.zeros((0, 1), dtype=np.float32))
            self.meta_path.write_text("[]")
            return
        np.save(self.vec_path, self._vectors)
        self.meta_path.write_text(
            json.dumps([asdict(r) for r in self._records], ensure_ascii=False)
        )

    def add(self, vectors: np.ndarray, records: list[VectorRecord]) -> None:
        if len(records) == 0:
            return
        vectors = np.asarray(vectors, dtype=np.float32)
        with self._lock:
            if self._vectors is None or len(self._records) == 0:
                self._vectors = vectors
            else:
                if vectors.shape[1] != self._vectors.shape[1]:
                    raise ValueError(
                        "Embedding dimension changed; clear the index before "
                        "re-ingesting with a different embedder."
                    )
                self._vectors = np.vstack([self._vectors, vectors])
            self._records.extend(records)
            self._persist()

    def search(self, query_vec: np.ndarray, top_k: int) -> list[SearchHit]:
        with self._lock:
            if self._vectors is None or len(self._records) == 0:
                return []
            q = np.asarray(query_vec, dtype=np.float32).reshape(-1)
            if q.shape[0] != self._vectors.shape[1]:
                return []
            sims = self._vectors @ q  # vectors are L2-normalized
            k = min(top_k, len(self._records))
            idx = np.argpartition(-sims, k - 1)[:k]
            idx = idx[np.argsort(-sims[idx])]
            return [SearchHit(record=self._records[i], score=float(sims[i])) for i in idx]

    def delete_file(self, file_id: str) -> int:
        with self._lock:
            if not self._records:
                return 0
            keep = [i for i, r in enumerate(self._records) if r.file_id != file_id]
            removed = len(self._records) - len(keep)
            if removed:
                self._records = [self._records[i] for i in keep]
                self._vectors = (
                    self._vectors[keep] if self._vectors is not None and keep else None
                )
                self._persist()
            return removed

    def list_files(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._records:
            counts[r.file_id] = counts.get(r.file_id, 0) + 1
        return counts

    def clear(self) -> None:
        with self._lock:
            self._vectors = None
            self._records = []
            self._persist()

    def count(self) -> int:
        return len(self._records)


_store_singleton: Optional[VectorStore] = None


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    global _store_singleton
    if _store_singleton is not None:
        return _store_singleton
    settings = settings or get_settings()
    if settings.vector_store == "chroma":
        try:
            from .chroma_store import ChromaVectorStore  # type: ignore

            _store_singleton = ChromaVectorStore(settings.vector_dir)
            return _store_singleton
        except Exception:
            pass  # fall back to numpy
    _store_singleton = NumpyVectorStore(settings.vector_dir)
    return _store_singleton


def reset_vector_store() -> None:
    """Used by tests to force a fresh store."""
    global _store_singleton
    _store_singleton = None
