"""Ortak ayarlar — .env, router corpus/index yolları."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
DB_PKG = (
    PROJECT_ROOT
    / "veritabani_kurgusu_test_seneryolari"
    / "veritabani_kurgusu_test_seneryolari"
)

CONFIG_PATH = ROOT / "config" / "router_config.json"

_DEFAULTS: dict[str, Any] = {
    "active_dataset": "legacy_augmented",
    "corpus_path": "data/processed/chatbot_dataset_augmented.json",
    "vector_index_path": "data/processed/embeddings.npz",
    "metadata_path": "data/processed/index_meta.json",
    "index_dir": "data/processed",
}


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        return
    if (DB_PKG / ".env").exists():
        _load(DB_PKG / ".env")
    _load(ROOT / ".env", override=True)


def get_database_url() -> str:
    load_dotenv()
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL yok. chatbot_demo/.env oluşturun veya "
            "python -m scripts.setup_local_db çalıştırın."
        )
    return url


def configure_windows_pg_dll() -> None:
    if sys.platform != "win32":
        return
    pg_base = r"C:\Program Files\PostgreSQL"
    if not os.path.exists(pg_base):
        return
    for version in os.listdir(pg_base):
        pg_bin = os.path.join(pg_base, version, "bin")
        if os.path.isdir(pg_bin):
            try:
                os.add_dll_directory(pg_bin)
            except Exception:
                pass


def _resolve(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (ROOT / p)


def load_router_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return dict(_DEFAULTS)
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = dict(_DEFAULTS)
    cfg.update(raw)
    return cfg


def save_router_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def active_paths() -> dict[str, Any]:
    cfg = load_router_config()
    return {
        "corpus": _resolve(cfg["corpus_path"]),
        "vectors": _resolve(cfg["vector_index_path"]),
        "metadata": _resolve(cfg["metadata_path"]),
        "index_dir": _resolve(cfg.get("index_dir", "data/processed")),
        "active_dataset": cfg.get("active_dataset", "unknown"),
    }


# Allintos dijital olgunluk formu — pipeline slug → sector_key query param
_SECTOR_DIGITAL_MATURITY_KEYS: dict[str, str] = {
    "saglik": "health",
    "egitim": "education",
    "eglence": "entertainment",
    "turizm": "tourism",
    "bilisim": "information_technology",
}


def get_allintos_site_url() -> str:
    load_dotenv()
    return (os.getenv("ALLINTOS_SITE_URL") or "http://10.20.40.154:5000").rstrip("/")


def sector_digital_maturity_url(sector: str) -> str:
    """Sektör slug → Allintos dijital olgunluk sayfası URL'si."""
    sector_key = _SECTOR_DIGITAL_MATURITY_KEYS.get((sector or "").strip().lower())
    if not sector_key:
        return ""
    base = get_allintos_site_url()
    return f"{base}/dijital-olgunluk?sector_key={sector_key}"


def intent_form_urls() -> dict[str, str]:
    """Intent code → form URL (seed / intents tablosu ile hizalı)."""
    return {
        "health_appointment": sector_digital_maturity_url("saglik"),
        "tourism_hotel": sector_digital_maturity_url("turizm"),
        "education_enrollment": sector_digital_maturity_url("egitim"),
        "bilisim_integration": sector_digital_maturity_url("bilisim"),
        "eglence_streaming": sector_digital_maturity_url("eglence"),
        "sector_form_request": f"{get_allintos_site_url()}/dijital-olgunluk",
    }
