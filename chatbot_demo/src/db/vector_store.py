"""V2 Stage-1 retrieval — pgvector ANN (cosine) Top-K."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.db.connection import get_engine
from src.db.migrate import ensure_schema
from src.db.schema import EMBEDDING_DIM, TABLE_NAME


@dataclass(frozen=True)
class VectorCandidate:
    """pgvector adayı — reranker girdisi."""

    id: int
    source_id: str
    sector: str
    sub_intent: str
    text_content: str
    distance: float  # cosine distance (0 = özdeş)
    score: float  # 1 - distance (yaklaşık benzerlik)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "sector": self.sector,
            "sub_intent": self.sub_intent,
            "text_content": self.text_content,
            "distance": self.distance,
            "score": self.score,
        }


def _vec_literal(embedding: Sequence[float] | np.ndarray) -> str:
    arr = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if arr.shape[0] != EMBEDDING_DIM:
        raise ValueError(
            f"embedding dim {arr.shape[0]} != expected {EMBEDDING_DIM}"
        )
    return "[" + ",".join(f"{float(x):.8f}" for x in arr.tolist()) + "]"


class VectorIndexStore:
    """
    Paralel V2 retrieval servisi (SQL cosine <=> + HNSW).
    V1 NPZ / Chatbot.sor() yoluna dokunmaz.
    """

    backend = "pgvector"

    def __init__(self, engine: Engine | None = None, *, auto_migrate: bool = True) -> None:
        self._engine = engine or get_engine()
        if auto_migrate:
            ensure_schema(self._engine)

    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]:
        """Cosine ANN — HNSW indeksi üzerinden Top-K."""
        if top_k < 1:
            return []
        lit = _vec_literal(query_embedding)
        # <=> = cosine distance (pgvector)
        where = ""
        params: dict[str, Any] = {"k": int(top_k)}
        if sector:
            where = "WHERE sector = :sector"
            params["sector"] = sector

        sql = text(
            f"""
            SELECT
                id,
                source_id,
                sector,
                sub_intent,
                text_content,
                (embedding <=> CAST(:emb AS vector)) AS distance
            FROM {TABLE_NAME}
            {where}
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :k
            """
        )
        params["emb"] = lit

        with self._engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()

        out: list[VectorCandidate] = []
        for r in rows:
            dist = float(r["distance"])
            out.append(
                VectorCandidate(
                    id=int(r["id"]),
                    source_id=str(r["source_id"]),
                    sector=str(r["sector"]),
                    sub_intent=str(r["sub_intent"]),
                    text_content=str(r["text_content"]),
                    distance=round(dist, 6),
                    score=round(max(0.0, 1.0 - dist), 6),
                )
            )
        return out

    def upsert_batch(
        self,
        rows: list[dict[str, Any]],
        *,
        batch_size: int = 200,
    ) -> int:
        """
        rows: source_id, sector, sub_intent, text_content, embedding[, lang, meta]
        ON CONFLICT (source_id) DO UPDATE.
        """
        if not rows:
            return 0
        sql = text(
            f"""
            INSERT INTO {TABLE_NAME}
                (source_id, sector, sub_intent, text_content, embedding, lang, meta)
            VALUES (
                :source_id,
                :sector,
                :sub_intent,
                :text_content,
                CAST(:embedding AS vector),
                :lang,
                CAST(:meta AS jsonb)
            )
            ON CONFLICT (source_id) DO UPDATE SET
                sector = EXCLUDED.sector,
                sub_intent = EXCLUDED.sub_intent,
                text_content = EXCLUDED.text_content,
                embedding = EXCLUDED.embedding,
                lang = EXCLUDED.lang,
                meta = EXCLUDED.meta
            """
        )
        n = 0
        with self._engine.begin() as conn:
            for i in range(0, len(rows), batch_size):
                chunk = rows[i : i + batch_size]
                payload = []
                for r in chunk:
                    emb = r["embedding"]
                    payload.append(
                        {
                            "source_id": str(r["source_id"]),
                            "sector": str(r["sector"]),
                            "sub_intent": str(r["sub_intent"]),
                            "text_content": str(r["text_content"]),
                            "embedding": _vec_literal(emb),
                            "lang": str(r.get("lang") or "tr"),
                            "meta": __import__("json").dumps(r.get("meta") or {}),
                        }
                    )
                conn.execute(sql, payload)
                n += len(payload)
        return n
