"""Embedding providers.

Default is a **local hashing embedder** — deterministic, dependency-free, and
good enough for keyword-ish semantic retrieval on small local corpora. It
means RAG works out of the box with zero downloads. For better quality the
user can switch ``EMBEDDING_PROVIDER`` to ``sentence_transformers`` or
``ollama`` (both lazy-imported so they remain optional).
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

from ..config import Settings, get_settings

_WORD = re.compile(r"[a-zA-Z0-9]+")


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalized vectors."""

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


def _l2norm(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class HashingEmbedder(Embedder):
    """Feature-hashing bag-of-words embedder with sub-word shingles.

    Stable across runs/processes (uses md5, not Python's salted hash). Captures
    token overlap well enough for retrieving the right chunks locally.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _hash(self, token: str) -> int:
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(h[:8], 16) % self.dim

    def _vec(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _WORD.findall(text.lower())
        for tok in tokens:
            vec[self._hash(tok)] += 1.0
            # character trigrams add fuzzy matching
            for i in range(len(tok) - 2):
                vec[self._hash(tok[i : i + 3])] += 0.5
        # sublinear scaling
        nz = vec > 0
        vec[nz] = 1.0 + np.log(vec[nz])
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        mat = np.vstack([self._vec(t) for t in texts])
        return _l2norm(mat).astype(np.float32)


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # lazy

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)


class OllamaEmbedder(Embedder):
    def __init__(self, base_url: str, model: str = "nomic-embed-text", dim: int = 768):
        import httpx  # lazy

        self._httpx = httpx
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = []
        with self._httpx.Client(timeout=60.0) as client:
            for t in texts:
                r = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": t},
                )
                r.raise_for_status()
                out.append(r.json()["embedding"])
        mat = np.asarray(out, dtype=np.float32)
        self.dim = mat.shape[1] if mat.size else self.dim
        return _l2norm(mat).astype(np.float32)


def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    provider = settings.embedding_provider
    try:
        if provider == "sentence_transformers":
            return SentenceTransformerEmbedder(settings.embedding_model)
        if provider == "ollama":
            return OllamaEmbedder(settings.ollama_base_url)
    except Exception:  # noqa: BLE001 — fall back to always-available embedder
        pass
    return HashingEmbedder(settings.embedding_dim)
