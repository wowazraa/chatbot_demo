"""clean_v1 corpus + NPZ embeddings → pgvector `vector_index` seed.

    # Yerel Postgres (5432) + chatbot_demo/.env hazır olsun:
    python -m db_api.setup_local_db
    python scripts/seed_pgvector.py --truncate
    python scripts/seed_pgvector.py --limit 100

NPZ'deki BGE-M3 vektörlerini yeniden encode etmeden aktarır.
HNSW (cosine) indeksi migrate ile oluşur.
V1 NPZ / Python geliştirme yolu kısıtlanmaz; DB yoksa seed exit 1,
runtime ise NPZ-dense fallback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.db.connection import get_connection_url, get_engine, reset_engine
from src.db.migrate import ensure_schema, row_count
from src.db.schema import EMBEDDING_DIM, TABLE_NAME
from src.db.vector_store import VectorIndexStore
from src.intent_router_contract import map_sector, map_sub_intent
from src.router_config import active_paths


def _load_clean_corpus() -> tuple[list[dict], np.ndarray]:
    paths = active_paths()
    corpus_path = Path(paths["corpus"])
    npz_path = Path(paths["vectors"])
    if not corpus_path.is_file():
        raise FileNotFoundError(f"Corpus yok: {corpus_path}")
    if not npz_path.is_file():
        raise FileNotFoundError(f"NPZ yok: {npz_path}")

    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    kayitlar = data.get("kayitlar") or []
    vectors = np.load(npz_path)["vectors"].astype(np.float32)
    if vectors.ndim != 2 or vectors.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"NPZ shape {vectors.shape} beklenen (*, {EMBEDDING_DIM}) değil"
        )
    if len(kayitlar) != vectors.shape[0]:
        raise ValueError(
            f"Kayıt sayısı ({len(kayitlar)}) != NPZ satır ({vectors.shape[0]})"
        )
    return kayitlar, vectors


def _build_rows(
    kayitlar: list[dict],
    vectors: np.ndarray,
    *,
    limit: int | None,
) -> list[dict]:
    n = len(kayitlar) if limit is None else min(limit, len(kayitlar))
    rows: list[dict] = []
    for i in range(n):
        rec = kayitlar[i]
        text = (rec.get("normalize_mesaj") or rec.get("mesaj") or "").strip()
        if not text:
            continue
        sector = map_sector(str(rec.get("beklenen_sektor") or ""))
        sub = map_sub_intent(sector, text)
        rows.append(
            {
                "source_id": str(rec.get("id") or f"row_{i}"),
                "sector": sector,
                "sub_intent": sub,
                "text_content": text,
                "embedding": vectors[i],
                "lang": str(rec.get("lang") or "tr"),
                "meta": {
                    "beklenen_mod": rec.get("beklenen_mod"),
                    "zorluk": rec.get("zorluk"),
                    "source_id_num": rec.get("source_id"),
                    "varyant": rec.get("varyant"),
                },
            }
        )
    return rows


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Seed vector_index from clean_v1 NPZ")
    ap.add_argument("--truncate", action="store_true", help=f"TRUNCATE {TABLE_NAME}")
    ap.add_argument("--limit", type=int, default=None, help="İlk N kayıt (duman)")
    ap.add_argument("--batch-size", type=int, default=200)
    args = ap.parse_args()

    reset_engine()
    print(f"[seed] DATABASE_URL = {get_connection_url()}")
    print("[seed] clean_v1 NPZ yükleniyor…")
    kayitlar, vectors = _load_clean_corpus()
    print(f"[seed] corpus={len(kayitlar)}  npz={vectors.shape}")

    rows = _build_rows(kayitlar, vectors, limit=args.limit)
    print(f"[seed] upsert adayı={len(rows)}")

    engine = get_engine()
    t0 = time.perf_counter()
    try:
        ensure_schema(engine)
    except Exception as exc:
        print("[seed] FAIL — pgvector DB hazır değil.")
        print(f"[seed] {exc}")
        print(
            "[seed] Önce yerel Postgres + python -m db_api.setup_local_db\n"
            "[seed] Runtime DB yokken NPZ-dense fallback ile çalışmaya devam eder."
        )
        return 1

    if args.truncate:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY"))
        print(f"[seed] TRUNCATE {TABLE_NAME}")

    store = VectorIndexStore(engine, auto_migrate=False)
    n = store.upsert_batch(rows, batch_size=args.batch_size)
    elapsed = time.perf_counter() - t0
    total = row_count(engine)
    print(f"[seed] upserted={n}  table_rows={total}  elapsed={elapsed:.1f}s")
    print("[seed] OK — HNSW cosine index hazır; V1 NPZ yolu değişmedi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
