"""
Canli motor yol guncellemesi
============================
Temiz (2195) veya legacy (8470) indekse gecis.

    python scripts/update_engine_paths.py
    python scripts/update_engine_paths.py --legacy
    python scripts/update_engine_paths.py --status
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.router_config import CONFIG_PATH, load_router_config, save_router_config

CLEAN = {
    "active_dataset": "clean_v1",
    "corpus_path": "data/processed/chatbot_dataset_clean.json",
    "vector_index_path": "data/processed/chatbot_dataset_clean_embeddings.npz",
    "metadata_path": "data/processed/chatbot_dataset_clean_index_meta.json",
    "index_dir": "data/processed",
    "notes": "Faz 1 temiz indeks. Geri: python scripts/update_engine_paths.py --legacy",
}

LEGACY = {
    "active_dataset": "legacy_augmented",
    "corpus_path": "data/processed/chatbot_dataset_augmented.json",
    "vector_index_path": "data/processed/embeddings.npz",
    "metadata_path": "data/processed/index_meta.json",
    "index_dir": "data/processed",
    "notes": "Eski augmented indeks (8470).",
}


def _exists(rel: str) -> bool:
    p = Path(rel)
    path = p if p.is_absolute() else ROOT / p
    return path.is_file()


def _status() -> None:
    cfg = load_router_config()
    print("=" * 60)
    print("INTENT ROUTER — AKTIF YOLLAR")
    print("=" * 60)
    print(f"Config         : {CONFIG_PATH}")
    print(f"active_dataset : {cfg.get('active_dataset')}")
    for key in ("corpus_path", "vector_index_path", "metadata_path"):
        rel = cfg.get(key, "")
        ok = _exists(str(rel))
        mark = "OK" if ok else "EKSIK"
        print(f"  [{mark}] {key}: {rel}")
    print("=" * 60)


def switch_to_clean_index(*, legacy: bool = False) -> None:
    print("=" * 60)
    print("INTENT ROUTER CANLI MOTOR YOL GUNCELLEMESI")
    print("=" * 60)

    target = LEGACY if legacy else CLEAN
    label = "LEGACY (8470)" if legacy else "CLEAN (2195)"

    for key in ("corpus_path", "vector_index_path", "metadata_path"):
        rel = target[key]
        if not _exists(rel):
            print(f"[HATA] Dosya yok: {rel}")
            if not legacy:
                print("       Once: python scripts/run_final_deduplication.py")
                print("             python scripts/build_clean_index.py")
            sys.exit(1)

    print(f"[+] Hedef: {label}")
    for key in ("corpus_path", "vector_index_path", "metadata_path"):
        print(f"    - {key}: {target[key]}")

    save_router_config(target)
    print(f"[+] Yazildi: {CONFIG_PATH}")
    print("-" * 60)
    print("Motor bir sonraki baslatmada bu indeksi yukleyecek.")
    print("Demo/server yeniden baslat: python demo/server.py")
    print("=" * 60)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", action="store_true", help="Eski 8470 indekse don")
    ap.add_argument("--status", action="store_true", help="Aktif yollari goster")
    args = ap.parse_args()

    if args.status:
        _status()
        return
    switch_to_clean_index(legacy=args.legacy)


if __name__ == "__main__":
    main()
