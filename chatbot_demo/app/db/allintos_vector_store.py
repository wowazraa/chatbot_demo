"""Allintos qa_embeddings uzerinden canli vektor arama (readonly)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from app.core.intent_contract import map_sub_intent
from app.core.intent_mapping import SEKTOR_TO_INTENT
from app.db.allintos_db import CANONICAL_SERVICE_INTENT_CODES, SERVICE_SECTORS, fetch_readonly
from app.db.vector_store import VectorCandidate, _vec_literal


_INTENT_TO_SECTOR = {SEKTOR_TO_INTENT[s]: s for s in SERVICE_SECTORS}


class AllintosQaEmbeddingStore:
    """Sinem qa_embeddings + intents — salt okunur retrieval."""

    backend = "allintos"

    def search(
        self,
        query_embedding: Sequence[float] | np.ndarray,
        *,
        top_k: int = 3,
        sector: str | None = None,
    ) -> list[VectorCandidate]:
        if top_k < 1:
            return []

        lit = _vec_literal(query_embedding)
        params: list[Any] = [lit, list(CANONICAL_SERVICE_INTENT_CODES), lit, int(top_k)]

        sql = """
            SELECT q.id, q.question, i.intent_code,
                   (q.embedding <=> CAST(%s AS vector)) AS distance
            FROM qa_embeddings q
            JOIN intents i ON q.intent_id = i.id
            WHERE i.intent_code = ANY(%s)
            ORDER BY q.embedding <=> CAST(%s AS vector)
            LIMIT %s
        """
        rows = fetch_readonly(sql, tuple(params))

        results: list[VectorCandidate] = []
        for row_id, question, intent_code, distance in rows:
            sec = _INTENT_TO_SECTOR.get(str(intent_code), "ood")
            if sector and sec != sector:
                continue
            dist = float(distance)
            sub = map_sub_intent(sec, question) if sec != "ood" else "ood.none"
            results.append(
                VectorCandidate(
                    id=int(row_id),
                    source_id=str(row_id),
                    sector=sec,
                    sub_intent=sub,
                    text_content=question,
                    distance=round(dist, 6),
                    score=round(max(0.0, 1.0 - dist), 6),
                    record_meta={"intent_code": intent_code, "backend": "allintos"},
                )
            )
            if len(results) >= top_k:
                break
        return results
