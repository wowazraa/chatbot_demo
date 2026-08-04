"""Kayıt ID üretimi — raw, augmented ve pgvector kaynaklarını birleştirir."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db.connection import get_engine


def _parse_numeric_id(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s.isdigit():
        return int(s)
    return None


def max_numeric_id_from_records(records: list[dict]) -> int:
    mx = 0
    for rec in records:
        for key in ("id", "source_id"):
            n = _parse_numeric_id(rec.get(key))
            if n is not None:
                mx = max(mx, n)
    return mx


def max_numeric_id_from_pg() -> int:
    """Postgres vector_index source_id kolonundaki en büyük sayısal ID."""
    try:
        eng = get_engine()
        with eng.connect() as conn:
            rows = conn.execute(text("SELECT source_id FROM vector_index")).fetchall()
    except Exception:
        return 0

    mx = 0
    for (sid,) in rows:
        n = _parse_numeric_id(sid)
        if n is not None:
            mx = max(mx, n)
    return mx


def compute_next_record_id(
    raw_records: list[dict],
    aug_records: list[dict] | None = None,
    *,
    include_pg: bool = True,
) -> int:
    """Üç kaynaktaki en yüksek sayısal ID + 1."""
    candidates = [
        max_numeric_id_from_records(raw_records),
        max_numeric_id_from_records(aug_records or []),
    ]
    if include_pg:
        candidates.append(max_numeric_id_from_pg())
    return max(candidates) + 1
