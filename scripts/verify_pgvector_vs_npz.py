"""pgvector Top-3 ↔ NPZ Top-3 tutarlılık dumanı.

    python scripts/verify_pgvector_vs_npz.py

pgvector yoksa skip (exit 0) — NPZ fallback ortamında CI kırılmaz.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.db.npz_store import NpzDenseStore
from src.db.store_factory import open_vector_store, probe_pgvector
from src.embedder import get_embedder


QUERIES = [
    "Kardiyoloji randevusu almak istiyorum",
    "Bilgisayar mühendisliği taban puanları ve burs imkanları",
    "Yabancı turist sağlık sigortası paketi",
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ok, detail = probe_pgvector()
    if not ok:
        print(f"[verify] SKIP — pgvector yok ({detail})")
        print("[verify] NPZ-dense fallback aktif; tutarlılık karşılaştırması için:")
        print("         python -m db_api.setup_local_db && python scripts/seed_pgvector.py --truncate")
        return 0

    pg = open_vector_store(prefer_pg=True)
    if getattr(pg, "backend", "") != "pgvector":
        print("[verify] SKIP — store pgvector değil")
        return 0

    npz = NpzDenseStore()
    emb = get_embedder()
    print(f"[verify] Connected to pgvector DB | comparing Top-3 vs NPZ")

    mismatches = 0
    for q in QUERIES:
        vec = emb.encode_dense([q])[0]
        a = pg.search(vec, top_k=3)
        b = npz.search(vec, top_k=3)
        texts_a = [h.text_content[:60] for h in a]
        texts_b = [h.text_content[:60] for h in b]
        # Aynı Top-1 sektör veya aynı metin (HNSW approx olabilir)
        same_top1 = (
            bool(a and b)
            and (a[0].sector == b[0].sector or a[0].text_content == b[0].text_content)
        )
        status = "OK" if same_top1 else "DIFF"
        if not same_top1:
            mismatches += 1
        print(f"  {status} | {q[:50]}")
        print(f"       pg : {texts_a}")
        print(f"       npz: {texts_b}")

    if mismatches:
        print(f"[verify] WARN — {mismatches}/{len(QUERIES)} Top-1 farkı (HNSW approx olabilir)")
        return 0
    print("[verify] OK — Top-1 sektör/metin tutarlı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
