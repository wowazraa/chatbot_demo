"""Vektör benzerlik araması — BGE-M3 embedding + pgvector/NPZ."""

from __future__ import annotations

from typing import Callable

import numpy as np

from app.core.torch_runtime import configure_torch_threads
from app.db.store_factory import open_vector_store
from app.db.vector_store import VectorCandidate
from app.services.embedder import BGEEmbedder, get_embedder, reset_embedder


class SimilarityService:
    """Katman 2 — embedding üretimi ve vektör arama."""

    def __init__(self, *, store=None, embed_fn: Callable[[str], np.ndarray] | None = None, top_k: int = 3):
        self._store = store
        self._embed_fn = embed_fn
        self.top_k = max(1, min(3, int(top_k)))

    @property
    def store(self):
        if self._store is None:
            self._store = open_vector_store(prefer_pg=True)
        return self._store

    def reset_embedder(self) -> None:
        reset_embedder()

    def embed_query(self, query: str) -> np.ndarray:
        if self._embed_fn is not None:
            return np.asarray(self._embed_fn(query), dtype=np.float32)
        configure_torch_threads(4)
        emb = get_embedder()
        return emb.encode_dense([query])[0]

    def search(self, query: str, *, top_k: int | None = None) -> list[VectorCandidate]:
        k = top_k if top_k is not None else self.top_k
        vec = self.embed_query(query)
        return self.store.search(vec, top_k=k)

    @staticmethod
    def build_embedder() -> BGEEmbedder:
        return BGEEmbedder()


__all__ = ["SimilarityService", "VectorCandidate", "get_embedder", "reset_embedder"]
