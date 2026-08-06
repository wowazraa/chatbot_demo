"""
Manuel retrieval karsilastirma — local vs Allintos.

Kullanim:
    python scripts/test_allintos_retrieval_manual.py
    python scripts/test_allintos_retrieval_manual.py --mode primary
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

QUERIES = [
    ("hastane yonetim sistemi ariyoruz", "saglik"),
    ("otel rezervasyon yazilimi istiyoruz", "turizm"),
    ("okul yonetim sistemi arayisindayiz", "egitim"),
    ("kurumsal ERP entegrasyonu", "bilisim"),
    ("streaming platformu gelistirmek istiyoruz", "eglence"),
]


def run_mode(mode: str) -> None:
    os.environ["ALLINTOS_RETRIEVAL_MODE"] = mode
    from app.services.similarity_service import SimilarityService

    svc = SimilarityService(top_k=3)
    print(f"\n=== mode={mode} backend={getattr(svc.store, 'backend', '?')} ===")
    matches = 0
    for query, expected in QUERIES:
        hits = svc.search(query, top_k=3)
        top = hits[0].sector if hits else "?"
        ok = top == expected
        matches += int(ok)
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {query!r} -> top1={top} (beklenen={expected}) score={hits[0].score if hits else 0:.3f}")
    print(f"  Sonuc: {matches}/{len(QUERIES)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("local", "primary", "both"), default="both")
    args = parser.parse_args()

    if args.mode in ("local", "both"):
        run_mode("local")
    if args.mode in ("primary", "both"):
        from app.db.allintos_db import fetch_readonly

        cnt = fetch_readonly("SELECT COUNT(*) FROM qa_embeddings")[0][0]
        if cnt == 0:
            print("\n[!] qa_embeddings bos — once backfill calistirin.")
            sys.exit(1)
        run_mode("primary")


if __name__ == "__main__":
    main()
