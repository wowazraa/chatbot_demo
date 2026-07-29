"""
Intent Router — aktif corpus / indeks yollari
=============================================
Tek kaynak: config/router_config.json
 guuncelle: python scripts/update_engine_paths.py
            python scripts/update_engine_paths.py --legacy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "router_config.json"

_DEFAULTS: dict[str, Any] = {
    "active_dataset": "legacy_augmented",
    "corpus_path": "data/processed/chatbot_dataset_augmented.json",
    "vector_index_path": "data/processed/embeddings.npz",
    "metadata_path": "data/processed/index_meta.json",
    "index_dir": "data/processed",
}


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
