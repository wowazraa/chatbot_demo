"""Kayıt tipi ayrımı — hizmet sektörü vs kurumsal bilgi (6. sektör DEĞİL)."""

from __future__ import annotations

from typing import Any

# Dataset + index meta sabitleri
KAYIT_TIPI_HIZMET = "hizmet_niyeti"
KAYIT_TIPI_KURUMSAL = "kurumsal_bilgi"
KAYIT_TIPI_FALLBACK = "fallback"

KAYIT_TIPLERI = frozenset({KAYIT_TIPI_HIZMET, KAYIT_TIPI_KURUMSAL, KAYIT_TIPI_FALLBACK})

# pgvector.sector sentinel — 5 hizmet sektörü listesine dahil edilmez
PG_SECTOR_INFO = "info"


def normalize_kayit_tipi(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in KAYIT_TIPLERI:
        return v
    return KAYIT_TIPI_HIZMET


def is_kurumsal_bilgi(rec: dict[str, Any]) -> bool:
    return normalize_kayit_tipi(rec.get("kayit_tipi")) == KAYIT_TIPI_KURUMSAL


def is_service_record(rec: dict[str, Any]) -> bool:
    return normalize_kayit_tipi(rec.get("kayit_tipi")) == KAYIT_TIPI_HIZMET


def konu_etiketi_from_zorluk(zorluk: str | None) -> str:
    """Desktop kurumsal kayıtları: zorluk alanı konu_etiketi taşıyıcısı."""
    z = (zorluk or "").strip()
    if z.startswith("kurumsal_"):
        return z
    if z:
        return f"kurumsal_{z}"
    return "kurumsal_unknown"


def transform_kurumsal_source_record(rec: dict[str, Any]) -> dict[str, Any]:
    """
    Desktop kurumsal kaydı → merge-ready kayıt.
    beklenen_sektor='kurumsal' kaldırılır; kayit_tipi + konu_etiketi eklenir.
    """
    out = dict(rec)
    out["kayit_tipi"] = KAYIT_TIPI_KURUMSAL
    out["konu_etiketi"] = konu_etiketi_from_zorluk(rec.get("zorluk"))
    out["beklenen_mod"] = rec.get("beklenen_mod") or "BILGI"
    out.pop("beklenen_sektor", None)
    return out


def infer_kayit_tipi_legacy(rec: dict[str, Any]) -> str:
    """Eski kayıtlarda kayit_tipi yoksa türet."""
    if rec.get("kayit_tipi"):
        return normalize_kayit_tipi(rec.get("kayit_tipi"))
    mod = (rec.get("beklenen_mod") or "").upper()
    sektor = (rec.get("beklenen_sektor") or "").strip().lower()
    if mod == "BILGI" or sektor == "kurumsal":
        return KAYIT_TIPI_KURUMSAL
    if sektor in ("belirsiz", "ood", "") or mod == "FB":
        return KAYIT_TIPI_FALLBACK
    return KAYIT_TIPI_HIZMET


__all__ = [
    "KAYIT_TIPI_HIZMET",
    "KAYIT_TIPI_KURUMSAL",
    "KAYIT_TIPI_FALLBACK",
    "KAYIT_TIPLERI",
    "PG_SECTOR_INFO",
    "normalize_kayit_tipi",
    "is_kurumsal_bilgi",
    "is_service_record",
    "konu_etiketi_from_zorluk",
    "transform_kurumsal_source_record",
    "infer_kayit_tipi_legacy",
]
