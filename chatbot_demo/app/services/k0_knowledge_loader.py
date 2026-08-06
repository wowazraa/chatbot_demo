"""Allintos knowledge_documents → K0 kayit formati donusumu."""

from __future__ import annotations

import json
import unicodedata
from typing import Any

from app.core.record_types import KAYIT_TIPI_KURUMSAL
from app.db.allintos_db import fetch_readonly, is_allintos_readonly_configured


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def fetch_knowledge_documents() -> list[dict[str, Any]]:
    """Aktif kurumsal knowledge_documents satirlarini getirir."""
    if not is_allintos_readonly_configured():
        return []

    rows = fetch_readonly(
        """
        SELECT id, document_code, title, content, source_url, metadata, language_code
        FROM knowledge_documents
        WHERE content_type = %s AND is_active = true
        ORDER BY id
        """,
        ("corporate",),
    )

    docs: list[dict[str, Any]] = []
    for doc_id, code, title, content, source_url, metadata, language_code in rows:
        meta = metadata if isinstance(metadata, dict) else json.loads(metadata or "{}")
        docs.append(
            {
                "id": int(doc_id),
                "document_code": code,
                "title": title,
                "content": content,
                "source_url": source_url,
                "metadata": meta,
                "language_code": language_code or "tr",
            }
        )
    return docs


def documents_to_k0_records(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Gruplu knowledge_documents → K0'nin bekledigi duz kayit listesi.
    Her metadata.queries satiri ayri virtual kayit olur.
    """
    records: list[dict[str, Any]] = []

    for doc in docs:
        meta = doc.get("metadata") or {}
        konu = str(meta.get("konu_etiketi") or "")
        lang = str(doc.get("language_code") or "tr").lower()[:2]
        cevap = (doc.get("content") or "").strip()
        if not cevap:
            continue

        queries = list(meta.get("queries") or [])
        norm_queries = list(meta.get("normalize_queries") or [])
        record_ids = list(meta.get("chatbot_record_ids") or [])

        title = (doc.get("title") or "").strip()
        if title and title not in queries:
            queries.insert(0, title)

        if not queries:
            queries = [title or konu or doc.get("document_code", "")]

        for idx, query in enumerate(queries):
            q = str(query or "").strip()
            if not q:
                continue
            norm = (
                str(norm_queries[idx]).strip()
                if idx < len(norm_queries) and norm_queries[idx]
                else _fold(q)
            )
            rec_id = record_ids[idx] if idx < len(record_ids) else doc.get("id")

            records.append(
                {
                    "id": rec_id,
                    "mesaj": q,
                    "ham_mesaj": q,
                    "normalize_mesaj": norm,
                    "cevap": cevap,
                    "konu_etiketi": konu,
                    "lang": lang,
                    "kayit_tipi": KAYIT_TIPI_KURUMSAL,
                    "kaynak_url": doc.get("source_url") or "",
                    "document_code": doc.get("document_code"),
                    "k0_source": "allintos",
                }
            )

    return records


def load_allintos_k0_records() -> list[dict[str, Any]]:
    docs = fetch_knowledge_documents()
    return documents_to_k0_records(docs)
