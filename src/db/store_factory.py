"""Vektör store seçici — pgvector varsa SQL, yoksa NPZ (çökmeden)."""

from __future__ import annotations

import logging
import math
from typing import Any, Protocol, Sequence

import numpy as np

from src.db.vector_store import VectorCandidate

logger = logging.getLogger("omniintent.vector_backend")


class VectorSearchStore(Protocol):
    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]: ...


class QaEmbeddingDbStore:
    backend = "database"

    def __init__(self) -> None:
        from db_api.bridge import SessionLocal
        self.SessionLocal = SessionLocal

    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]:
        db = self.SessionLocal()
        try:
            from db_api.bridge import QaEmbedding, Intent, USE_PGVECTOR
            from src.intent_router_contract import map_sub_intent
            from sqlalchemy import text

            # Maps intent_code to sector_key (standardized)
            intent_to_sector = {
                "health_appointment": "saglik",
                "tourism_hotel": "turizm",
                "education_enrollment": "egitim",
                "bilisim_integration": "bilisim",
                "eglence_streaming": "eglence",
                "sector_form_request": "ood"
            }

            # Maps sector_key to intent_codes
            sector_to_intents = {
                "saglik": ["health_appointment"],
                "turizm": ["tourism_hotel"],
                "egitim": ["education_enrollment"],
                "bilisim": ["bilisim_integration"],
                "eglence": ["eglence_streaming"],
                "ood": ["sector_form_request"]
            }

            if USE_PGVECTOR:
                # pgvector direct cosine distance
                lit = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
                sql = """
                    SELECT q.id, q.question, i.intent_code,
                           (q.embedding <=> CAST(:emb AS vector)) AS distance
                    FROM qa_embeddings q
                    JOIN intents i ON q.intent_id = i.id
                """
                params = {"emb": lit, "k": int(top_k)}
                if sector:
                    allowed_intents = sector_to_intents.get(sector, [])
                    if allowed_intents:
                        sql += " WHERE i.intent_code IN :intents"
                        params["intents"] = tuple(allowed_intents)
                sql += " ORDER BY q.embedding <=> CAST(:emb AS vector) LIMIT :k"

                rows = db.execute(text(sql), params).mappings().all()

                results = []
                for r in rows:
                    icode = r["intent_code"]
                    sec = intent_to_sector.get(icode, "ood")
                    sub = map_sub_intent(sec, r["question"]) if sec != "ood" else "ood.none"
                    score = float(1.0 - r["distance"])
                    results.append(
                        VectorCandidate(
                            id=r["id"],
                            source_id=str(r["id"]),
                            sector=sec,
                            sub_intent=sub,
                            text_content=r["question"],
                            distance=float(r["distance"]),
                            score=score,
                        )
                    )
                return results
            else:
                # Python-based cosine fallback over database rows
                q = db.query(QaEmbedding).join(Intent)
                rows = q.all()

                def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
                    dot = sum(x * y for x, y in zip(a, b))
                    na = math.sqrt(sum(x * x for x in a)) or 1e-12
                    nb = math.sqrt(sum(x * x for x in b)) or 1e-12
                    return 1.0 - (dot / (na * nb))

                candidates = []
                for r in rows:
                    icode = r.intent.intent_code
                    sec = intent_to_sector.get(icode, "ood")

                    if sector and sec != sector:
                        continue

                    dist = _cosine_distance(query_embedding, list(r.embedding))
                    sub = map_sub_intent(sec, r.question) if sec != "ood" else "ood.none"
                    candidates.append(
                        VectorCandidate(
                            id=r.id,
                            source_id=str(r.id),
                            sector=sec,
                            sub_intent=sub,
                            text_content=r.question,
                            distance=dist,
                            score=1.0 - dist,
                        )
                    )
                candidates.sort(key=lambda c: c.distance)
                return candidates[:top_k]

        finally:
            db.close()


def probe_pgvector() -> tuple[bool, str]:
    """
    (ok, detail). ok=True → vector extension + vector_index erişilebilir.
    """
    try:
        from src.db.connection import get_engine, reset_engine
        from src.db.migrate import ensure_schema, row_count, table_exists

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
    Tercihen QaEmbeddingDbStore (Veritabanı); bağlanamazsa NpzDenseStore.
    Uygulama asla çökmez — fallback loglanır.
    """
    if prefer_pg:
        try:
            from db_api.bridge import engine
            # Test DB connection
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            
            from src.db.vector_store import VectorIndexStore
            store = VectorIndexStore()
            msg = "Connected to database vector store (table: vector_index)"
            logger.info(msg)
            print(msg, flush=True)
            return store
        except Exception as exc:
            msg = "DB unreachable, falling back to NPZ-dense"
            logger.warning("%s | %s", msg, exc)
            print(f"{msg}\n  reason: {exc}", flush=True)

    from src.db.npz_store import NpzDenseStore

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
