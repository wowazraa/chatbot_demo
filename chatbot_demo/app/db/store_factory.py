"""Vektör store seçici — pgvector varsa SQL, yoksa NPZ (çökmeden)."""

from __future__ import annotations

import logging
from typing import Any, Protocol, Sequence

import numpy as np

from app.db.vector_store import VectorCandidate

logger = logging.getLogger("omniintent.vector_backend")


class VectorSearchStore(Protocol):
    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]: ...


def probe_pgvector() -> tuple[bool, str]:
    """
    (ok, detail). ok=True → vector extension + vector_index erişilebilir.
    """
    try:
        from app.db.connection import get_engine, reset_engine
        from app.db.migrate import ensure_schema, row_count, table_exists

        reset_engine()
        eng = get_engine()
        with eng.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        ensure_schema(eng)
        if not table_exists(eng):
            return False, "vector_index tablosu yok"
        n = row_count(eng)
        return True, f"rows={n}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def open_vector_store(*, prefer_pg: bool = True) -> Any:
    """
    ALLINTOS_RETRIEVAL_MODE=primary → Sinem qa_embeddings (readonly).
    Aksi halde yerel vector_index; bağlanamazsa NpzDenseStore.
    """
    from app.core.config import allintos_local_fallback_enabled, get_allintos_retrieval_mode

    mode = get_allintos_retrieval_mode()
    if mode == "primary":
        try:
            from app.db.allintos_vector_store import AllintosQaEmbeddingStore

            store = AllintosQaEmbeddingStore()
            msg = "Allintos qa_embeddings retrieval (readonly, mode=primary)"
            logger.info(msg)
            print(msg, flush=True)
            return store
        except Exception as exc:
            if not allintos_local_fallback_enabled():
                raise
            msg = "Allintos retrieval basarisiz, yerel store'a dusuluyor"
            logger.warning("%s | %s", msg, exc)
            print(f"{msg}\n  reason: {exc}", flush=True)

    if prefer_pg:
        try:
            from app.db.database import engine

            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")

            from app.db.vector_store import VectorIndexStore

            store = VectorIndexStore()
            msg = "Connected to database vector store (table: vector_index)"
            logger.info(msg)
            print(msg, flush=True)
            return store
        except Exception as exc:
            msg = "DB unreachable, falling back to NPZ-dense"
            logger.warning("%s | %s", msg, exc)
            print(f"{msg}\n  reason: {exc}", flush=True)

    from app.db.npz_store import NpzDenseStore

    store = NpzDenseStore()
    logger.info(
        "NPZ-dense active | dim=%s rows=%s",
        store._vectors.shape[1],
        store._vectors.shape[0],
    )
    print(
        f"[VectorBackend] NPZ-dense | rows={store._vectors.shape[0]} "
        f"dim={store._vectors.shape[1]}",
        flush=True,
    )
    return store
