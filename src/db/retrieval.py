"""V2 retrieval resolver — pgvector tercih, NPZ graceful fallback."""

from __future__ import annotations

import logging
from typing import Any, Protocol, Sequence

import numpy as np

from src.db.vector_store import VectorCandidate

logger = logging.getLogger("omniintent.retrieval")


class RetrievalStore(Protocol):
    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]: ...


def pgvector_available(*, min_rows: int = 1) -> bool:
    """Postgres + pgvector extension + seeded vector_index var mı?"""
    try:
        from src.db.connection import get_engine
        from src.db.migrate import row_count, table_exists
        from sqlalchemy import text

        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            has_ext = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                    ")"
                )
            ).scalar()
            if not has_ext:
                return False
        if not table_exists(eng):
            return False
        return row_count(eng) >= int(min_rows)
    except Exception as exc:
        logger.info("[retrieval] pgvector unavailable: %s", exc)
        return False


def resolve_vector_store(*, prefer_pgvector: bool = True) -> Any:
    """
    Canlı V2 store seçici.
    1) pgvector seeded → VectorIndexStore (SQL <=>)
    2) aksi halde NpzDenseStore (çökmeden fallback)
    """
    if prefer_pgvector and pgvector_available():
        from src.db.vector_store import VectorIndexStore

        store = VectorIndexStore(auto_migrate=False)
        store.backend = "pgvector"  # type: ignore[attr-defined]
        print("[retrieval] backend=pgvector (SQL cosine <=>)", flush=True)
        return store

    from src.db.npz_store import NpzDenseStore

    store = NpzDenseStore()
    print(
        "[retrieval] backend=npz-dense (pgvector yok/seed yok — graceful fallback)",
        flush=True,
    )
    return store
