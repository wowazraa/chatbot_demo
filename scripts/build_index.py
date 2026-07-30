"""
BGE-M3 Embedding Index Builder
================================
Bu script'i SADECE BİR KEZ çalıştırın (veya veri seti güncellenince tekrar).

Yaptığı:
  1) data/processed/chatbot_dataset_augmented.json'u okur
  2) BGE-M3 modelini indirir/yükler (~2.3GB, bir kez)
  3) Tüm kayıtları batch halinde embed eder
  4) data/processed/embeddings.npz + index_meta.json'a kaydeder

Çalıştırma:
    python scripts/build_index.py

Seçenekler:
    python scripts/build_index.py --raw          # artırılmış yerine ham veriyi kullan
    python scripts/build_index.py --batch 32     # batch boyutu (bellek kısıtlıysa)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.embedder import BGEEmbedder

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
RAW_FILE       = ROOT / "data" / "raw"       / "chatbot_dataset.json"
PROCESSED_FILE = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"
INDEX_DIR      = ROOT / "data" / "processed"


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------
def load_records(use_raw: bool = False) -> list[dict]:
    path = RAW_FILE if use_raw else PROCESSED_FILE
    if not path.exists():
        print(f"[!] Dosya bulunamadı: {path}")
        if not use_raw:
            print("    Önce çalıştırın: python src/data_augmented.py")
        sys.exit(1)

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    recs = data.get("kayitlar", data) if isinstance(data, dict) else data
    print(f"[+] {len(recs)} kayıt yüklendi: {path.name}")
    return recs


# ---------------------------------------------------------------------------
# Ana builder
# ---------------------------------------------------------------------------
def build(use_raw: bool = False, batch_size: int = 64) -> None:
    print("=" * 60)
    print("  BGE-M3 Embedding Index Builder")
    print("=" * 60)

    records = load_records(use_raw)

    # Metin ve metadata ayır
    texts: list[str] = []
    meta:  list[dict] = []

    msg_fields = ("mesaj", "message", "text", "input")

    for rec in records:
        msg = ""
        for f in msg_fields:
            if f in rec and isinstance(rec[f], str):
                msg = rec[f]
                break
        if not msg:
            continue

        texts.append(msg)
        meta.append({
            "id":              rec.get("id"),
            "source_id":       rec.get("source_id"),
            "beklenen_sektor": rec.get("beklenen_sektor", rec.get("beklened_sektor", "belirsiz")),
            "beklenen_mod":    rec.get("beklenen_mod",    rec.get("beklened_mod",    "K1")),
            "lang":            rec.get("lang", "tr"),
            "zorluk":          rec.get("zorluk", ""),
            "varyant":         rec.get("varyant", "duz"),
        })

    print(f"[+] Embed edilecek: {len(texts)} metin")
    print()

    embedder = BGEEmbedder()
    t0 = time.time()

    embedder.build_index(texts, meta, show_progress=True)

    elapsed = time.time() - t0
    print(f"\n[+] Embedding tamamlandı: {elapsed:.1f}s")

    embedder.save_index(INDEX_DIR)
    print(f"[+] Index kaydedildi -> {INDEX_DIR}")

    # Hızlı doğrulama
    print("\n--- Hızlı Test ---")
    test_queries = [
        "hastane yönetim sistemi",
        "We need a hotel booking platform",
        "military communication software",
        "online eğitim platformu",
        "fiyat teklifi",
    ]
    for q in test_queries:
        res = embedder.find_top_k(q, k=1)
        if res:
            r = res[0]
            print(
                f"  '{q[:45]}'\n"
                f"    -> [{r.metadata['beklenen_sektor']:8}] {r.score:.4f} | {r.text[:55]}"
            )
    print("\n[+] Index build tamamlandı!")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BGE-M3 Index Builder")
    parser.add_argument("--raw",   action="store_true", help="Artırılmış yerine ham veriyi kullan")
    parser.add_argument("--batch", type=int, default=64, help="Batch boyutu (varsayılan: 64)")
    args = parser.parse_args()

    build(use_raw=args.raw, batch_size=args.batch)
