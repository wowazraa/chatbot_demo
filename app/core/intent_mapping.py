"""Sektör etiketi → intent_code / pgvector sector — tek kaynak."""

from __future__ import annotations

import sys

SEKTOR_TO_INTENT: dict[str, str] = {
    "turizm": "tourism_hotel",
    "saglik": "health_appointment",
    "egitim": "education_enrollment",
    "bilisim": "bilisim_integration",
    "eglence": "eglence_streaming",
    "ood": "ood",
    "belirsiz": "ood",
}

_SEKTOR_NORMALIZE: dict[str, str] = {
    "sağlık": "saglik",
    "eğitim": "egitim",
    "turizm": "turizm",
    "bilişim": "bilisim",
    "eğlence": "eglence",
    "ood": "ood",
    "belirsiz": "belirsiz",
}

_PG_SECTOR_MAP: dict[str, str] = {
    "sağlık": "saglik",
    "eğitim": "egitim",
    "bilişim": "bilisim",
    "eğlence": "eglence",
    "turizm": "turizm",
    "health": "saglik",
    "education": "egitim",
    "it": "bilisim",
    "entertainment": "eglence",
    "hospitality": "turizm",
}

_VALID_PG_SECTORS = frozenset({"saglik", "turizm", "egitim", "bilisim", "eglence", "ood"})

ALLINTOS_INTENT_ID_MAP: dict[str, int] = {
    "turizm": 1,
    "saglik": 2,
    "egitim": 3,
    "bilisim": 4,
    "eglence": 5,
}


def resolve_intent(raw_sektor: str | None) -> str:
    """Ham sektör etiketini DB-uyumlu intent koduna dönüştürür."""
    if not raw_sektor:
        return "ood"

    normalized = _SEKTOR_NORMALIZE.get(raw_sektor.strip(), raw_sektor.strip())
    intent = SEKTOR_TO_INTENT.get(normalized)

    if intent is None:
        print(
            f"  [UYARI] Bilinmeyen sektör etiketi: '{raw_sektor}' → 'ood' atandı. "
            f"SEKTOR_TO_INTENT tablosunu güncelleyin.",
            file=sys.stderr,
        )
        return "ood"

    return intent


def normalize_pg_sector(raw_sektor: str | None) -> str:
    """vector_index.sector kolonu için ASCII slug."""
    raw = str(raw_sektor or "ood").lower().strip()
    sector = _PG_SECTOR_MAP.get(raw, raw)
    if sector not in _VALID_PG_SECTORS:
        return "ood"
    return sector


def source_id_for_record(rec: dict, *, fallback_index: int | None = None) -> str:
    """pgvector source_id — seed_pgvector ile aynı kural."""
    sid = rec.get("source_id") or rec.get("id")
    if sid is not None:
        return str(sid)
    if fallback_index is not None:
        return f"gen_{fallback_index}"
    raise ValueError(f"source_id/id yok: {rec}")


def build_index_meta_entry(rec: dict) -> tuple[str, dict]:
    """build_index.py ile uyumlu (text, meta) çifti."""
    msg_fields = ("mesaj", "message", "text", "input")
    msg = ""
    for field in msg_fields:
        if field in rec and isinstance(rec[field], str):
            msg = rec[field]
            break
    if not msg:
        raise ValueError(f"Kayıtta mesaj alanı yok: {rec}")

    raw_sektor = rec.get(
        "beklenen_sektor",
        rec.get("beklened_sektor", "belirsiz"),
    )
    intent_code = resolve_intent(raw_sektor)

    meta = {
        "id": rec.get("id"),
        "source_id": rec.get("source_id"),
        "beklenen_sektor": raw_sektor,
        "intent_code": intent_code,
        "beklenen_mod": rec.get("beklenen_mod", rec.get("beklened_mod", "K1")),
        "lang": rec.get("lang", "tr"),
        "zorluk": rec.get("zorluk", ""),
        "varyant": rec.get("varyant", "duz"),
    }
    return msg, meta
