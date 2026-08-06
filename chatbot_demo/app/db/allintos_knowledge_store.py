"""Kurumsal K2 fallback — knowledge_document_embeddings vector arama."""

from __future__ import annotations

import json
from typing import Any, Sequence

import numpy as np

from app.core.record_types import KAYIT_TIPI_KURUMSAL
from app.db.allintos_db import fetch_readonly
from app.db.vector_store import VectorCandidate, _vec_literal


def search_corporate_knowledge(
    query_embedding: Sequence[float] | np.ndarray,
    *,
    top_k: int = 50,
) -> list[VectorCandidate]:
    lit = _vec_literal(query_embedding)
    rows = fetch_readonly(
        """
        SELECT
            d.id,
            d.content,
            d.metadata,
            d.language_code,
            d.source_url,
            e.chunk_text,
            (e.embedding <=> CAST(%s AS vector)) AS distance
        FROM knowledge_document_embeddings e
        JOIN knowledge_documents d ON d.id = e.knowledge_document_id
        WHERE d.content_type = %s AND d.is_active = true
        ORDER BY e.embedding <=> CAST(%s AS vector)
        LIMIT %s
        """,
        (lit, "corporate", lit, int(top_k)),
    )

    out: list[VectorCandidate] = []
    for doc_id, content, metadata, lang, source_url, chunk_text, distance in rows:
        meta = metadata if isinstance(metadata, dict) else json.loads(metadata or "{}")
        dist = float(distance)
        score = max(0.0, 1.0 - dist)
        record_meta: dict[str, Any] = {
            "kayit_tipi": KAYIT_TIPI_KURUMSAL,
            "cevap": (content or "").strip(),
            "lang": lang or "tr",
            "konu_etiketi": meta.get("konu_etiketi") or "",
            "kaynak_url": source_url or "",
            "chunk_text": chunk_text,
            "k0_source": "allintos_knowledge_embeddings",
        }
        out.append(
            VectorCandidate(
                id=int(doc_id),
                source_id=str(doc_id),
                sector="ood",
                sub_intent="corporate_info.general",
                text_content=str(chunk_text or content or ""),
                distance=round(dist, 6),
                score=round(score, 6),
                record_meta=record_meta,
            )
        )
    return out
