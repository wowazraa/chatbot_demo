"""clean_v1 corpus + NPZ embeddings → pgvector `vector_index` seed.

    # Yerel Postgres (5432) + chatbot_demo/.env hazır olsun:
    python -m db_api.setup_local_db
    python scripts/seed_pgvector.py --truncate
    python scripts/seed_pgvector.py --limit 100

NPZ'deki BGE-M3 vektörlerini yeniden encode etmeden aktarır.
HNSW (cosine) indeksi migrate ile oluşur.
V1 NPZ / Python geliştirme yolu kısıtlanmaz; DB yoksa seed exit 1,
runtime ise NPZ-dense fallback.

DEĞİŞİKLİK (intent_code fix):
  - _build_rows() artık index_meta.json'dan intent_code'u birincil kaynak
    olarak okur; bu sayede build_index.py'deki SEKTOR_TO_INTENT eşlemesi
    doğrudan DB'ye yansır.
  - Ham beklened_sektor'a geri düşme (fallback) yalnızca meta eksikse çalışır.
  - map_sub_intent(seed_intent_code=...) aracılığıyla _SEED_TO_SUB tablosu
    artık gerçekten kullanılır.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# pyrefly: ignore [missing-import]
import numpy as np

from src.db.connection import get_connection_url, get_engine, reset_engine
from src.db.migrate import ensure_schema, row_count
from src.db.schema import EMBEDDING_DIM, TABLE_NAME
from src.db.vector_store import VectorIndexStore
from src.intent_router_contract import map_sector, map_sub_intent
from src.router_config import active_paths

# ---------------------------------------------------------------------------
# intent_code → sektör (build_index.py'deki SEKTOR_TO_INTENT'in tersi)
# map_sector() bunları zaten biliyor; bu tablo sadece _build_rows()'taki
# shortcut için kullanılır.
# ---------------------------------------------------------------------------
_INTENT_CODE_TO_SECTOR: dict[str, str] = {
    "tourism_hotel":          "turizm",
    "health_appointment":     "saglik",
    "education_enrollment":   "egitim",
    "bilisim_integration":    "bilisim",
    "eglence_streaming":      "eglence",
    "defense_communications": "savunma",
    "ood":                    "ood",
}


def _intent_code_to_sector(intent_code: str) -> str:
    """intent_code → map_sector()-uyumlu sektör string'i."""
    return _INTENT_CODE_TO_SECTOR.get((intent_code or "").strip().lower(), "ood")


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


def _load_index_meta(paths: dict) -> dict[str, dict]:
    """
    index_meta.json'u yükle ve source_id → meta dict olarak indeksle.

    build_index.py bu dosyayı 'intent_code' alanıyla yazar.
    Dosya yoksa boş dict döner; _build_rows() ham corpus etiketine fallback yapar.
    """
    meta_path = Path(paths["metadata"])
    if not meta_path.is_file():
        print(
            f"  [UYARI] index_meta.json bulunamadı: {meta_path}\n"
            "  intent_code eksik — ham etiket fallback kullanılacak.\n"
            "  Düzeltmek için: python scripts/build_index.py",
            file=sys.stderr,
        )
        return {}

    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    records: list[dict] = []
    if isinstance(raw, dict):
        records = raw.get("meta", raw.get("kayitlar", []))
    elif isinstance(raw, list):
        records = raw

    meta_by_id: dict[str, dict] = {}
    for m in records:
        sid = str(m.get("id") or m.get("source_id") or "")
        if sid:
            meta_by_id[sid] = m

    print(f"[seed] index_meta yüklendi: {len(meta_by_id)} kayıt")
    return meta_by_id


def _build_rows(
    kayitlar: list[dict],
    vectors: np.ndarray,
    meta_by_id: dict[str, dict],
    *,
    limit: int | None,
) -> list[dict]:
    """
    Her corpus kaydı için:
      1. DB-uyumlu intent_code'u index_meta.json'dan al   (birincil kaynak)
      2. Yoksa ham 'beklened_sektor' / 'beklenen_sektor' → map_sector() (fallback)
      3. map_sub_intent(seed_intent_code=...) aracılığıyla _SEED_TO_SUB tablosunu kullan
    """
    n = len(kayitlar) if limit is None else min(limit, len(kayitlar))
    rows: list[dict] = []
    fallback_count = 0

    for i in range(n):
        rec = kayitlar[i]
        text = (rec.get("normalize_mesaj") or rec.get("mesaj") or "").strip()
        if not text:
            continue

        source_id_val = str(rec.get("id") or f"row_{i}")

        # ── 1. intent_code'u index_meta'dan al ────────────────────────────
        meta_rec = meta_by_id.get(source_id_val, {})
        seed_intent_code: str | None = meta_rec.get("intent_code") or None

        # ── 2. Sektörü çöz ────────────────────────────────────────────────
        if seed_intent_code and seed_intent_code != "ood":
            sector = _intent_code_to_sector(seed_intent_code)
        else:
            # Fallback: corpus'taki ham etiket
            raw_sektor = str(
                rec.get("beklened_sektor")
                or rec.get("beklenen_sektor")
                or ""
            )
            sector = map_sector(raw_sektor)
            if not meta_rec:
                fallback_count += 1

        # ── 3. Sub-intent çöz ─────────────────────────────────────────────
        sub = map_sub_intent(sector, text, seed_intent_code=seed_intent_code)

        rows.append(
            {
                "source_id": source_id_val,
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
                    "intent_code": seed_intent_code,
                    "intent_code_src": "meta" if meta_rec else "fallback",
                    "raw_sektor": rec.get("beklened_sektor") or rec.get("beklenen_sektor"),
                },
            }
        )

    if fallback_count:
        print(
            f"  [UYARI] {fallback_count} kayıt için index_meta eşleşmesi bulunamadı "
            "(fallback kullanıldı). 'python scripts/build_index.py' ile yenileyin.",
            file=sys.stderr,
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

    paths = active_paths()
    kayitlar, vectors = _load_clean_corpus()
    print(f"[seed] corpus={len(kayitlar)}  npz={vectors.shape}")

    # index_meta.json — build_index.py'nin intent_code'larını içerir
    meta_by_id = _load_index_meta(paths)

    rows = _build_rows(kayitlar, vectors, meta_by_id, limit=args.limit)
    print(f"[seed] upsert adayı={len(rows)}")

    # Sektör dağılımı özeti (tanılama)
    dist = Counter(r["sector"] for r in rows)
    print("[seed] Sektör dağılımı:")
    for sec, cnt in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"       {sec:<20} {cnt:>5}")

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
        # pyrefly: ignore [missing-import]
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
