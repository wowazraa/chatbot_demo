"""Incremental index sync — NPZ + pgvector append (full rebuild değil)."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import psycopg2

from app.core.config import active_paths, load_dotenv
from app.core.intent_mapping import (
    build_index_meta_entry,
    normalize_pg_sector,
    source_id_for_record,
)
from app.core.record_types import infer_kayit_tipi_legacy, is_kurumsal_bilgi
from app.db.allintos_db import resolve_intent_id_for_sector
from app.db.vector_store import VectorIndexStore
from app.services.embedder import BGEEmbedder, reset_embedder

_sync_lock = threading.Lock()


class SourceIdCollisionError(RuntimeError):
    """index_meta'da zaten var olan source_id ile append denemesi."""


def _collect_existing_source_ids(meta: list[dict]) -> set[str]:
    ids: set[str] = set()
    for i, m in enumerate(meta):
        sid = m.get("source_id") if m.get("source_id") is not None else m.get("id")
        if sid is not None:
            ids.add(str(sid))
    return ids


def _assert_no_source_id_collisions(records: list[dict], paths: dict[str, Path]) -> None:
    """Append/upsert öncesi — duplicate source_id ile sessiz overwrite engellenir."""
    _, _, existing_meta, _ = _load_index_bundle(paths)
    existing = _collect_existing_source_ids(existing_meta)
    conflicts: list[str] = []
    for rec in records:
        sid = source_id_for_record(rec)
        if sid in existing:
            conflicts.append(sid)
    if conflicts:
        msg = (
            "[IndexSync] source_id cakismasi — islem durduruldu: "
            f"{sorted(set(conflicts))}. "
            "Bu ID index_meta.json'da zaten mevcut; duplicate append ve pg overwrite yapilmaz."
        )
        print(msg, flush=True)
        raise SourceIdCollisionError(msg)
_sync_embedder: BGEEmbedder | None = None


def _get_sync_embedder() -> BGEEmbedder:
    global _sync_embedder
    if _sync_embedder is None:
        _sync_embedder = BGEEmbedder()
    return _sync_embedder


def _atomic_replace(src: Path, dest: Path) -> None:
    """Windows/OneDrive uyumlu atomik degistirme."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"Kaynak dosya yok: {src}")
    backup = dest.with_suffix(dest.suffix + ".bak")
    if dest.exists():
        shutil.copy2(dest, backup)
    shutil.move(str(src), str(dest))
    if backup.exists():
        backup.unlink(missing_ok=True)


def _atomic_save_npz(path: Path, vectors: np.ndarray) -> None:
    # numpy.savez_compressed: .npz yoksa ekler — tmp dosya adi .npz ile bitsin
    tmp = path.with_name(f"{path.stem}.__tmp__.npz")
    if tmp.exists():
        tmp.unlink()
    np.savez_compressed(tmp, vectors=vectors)
    if not tmp.exists():
        raise FileNotFoundError(f"NPZ yazilamadi: {tmp}")
    _atomic_replace(tmp, path)


def _atomic_save_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(f"{path.stem}.__tmp__.json")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _atomic_replace(tmp, path)


def _assert_index_consistency(
    vectors: np.ndarray,
    texts: list[str],
    meta: list[dict],
    sparse_vectors: list[dict],
) -> None:
    n = vectors.shape[0]
    if not (len(texts) == len(meta) == len(sparse_vectors) == n):
        raise RuntimeError(
            "Index tutarsizligi: "
            f"vectors={n}, texts={len(texts)}, meta={len(meta)}, "
            f"sparse={len(sparse_vectors)}"
        )


def _load_index_bundle(paths: dict[str, Path]) -> tuple[np.ndarray, list[str], list[dict], list[dict]]:
    npz_path = paths["vectors"]
    meta_path = paths["metadata"]
    if not npz_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Index dosyalari yok. Once `python scripts/build_index.py` calistirin.\n"
            f"  {npz_path}\n  {meta_path}"
        )

    vectors = np.load(npz_path)["vectors"].astype(np.float32)
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    texts = list(payload.get("texts") or [])
    meta = list(payload.get("meta") or [])
    sparse_vectors = list(payload.get("sparse_vectors") or [])
    if len(sparse_vectors) < len(texts):
        sparse_vectors.extend({} for _ in range(len(texts) - len(sparse_vectors)))
    _assert_index_consistency(vectors, texts, meta, sparse_vectors)
    return vectors, texts, meta, sparse_vectors


def encode_new_records(
    records: list[dict],
) -> tuple[list[str], list[dict], np.ndarray, list[dict[str, float]]]:
    """Tek model yuklemesi — dense (L2-norm) + sparse."""
    if not records:
        raise ValueError("encode_new_records: bos liste")

    print(f"[IndexSync] Encode basliyor ({len(records)} kayit)...", flush=True)
    texts: list[str] = []
    meta: list[dict] = []
    for rec in records:
        msg, entry = build_index_meta_entry(rec)
        texts.append(msg)
        meta.append(entry)

    embedder = _get_sync_embedder()
    dense, sparse = embedder.encode_dense_and_sparse(texts)
    print(f"[IndexSync] Encode tamamlandi (dim={dense.shape[1]})", flush=True)
    return texts, meta, dense, sparse


def _sync_allintos(
    records: list[dict],
    dense_rows: np.ndarray,
) -> None:
    load_dotenv()
    if os.getenv("ALLINTOS_DB_ENABLED", "false").lower() != "true":
        print("[Allintos] ALLINTOS_DB_ENABLED=false, skipping DB insertion.")
        return

    db_url = os.getenv("ALLINTOS_DB_URL")
    if not db_url:
        print("[Allintos] ALLINTOS_DB_URL missing, skipping DB insertion.")
        return

    print(f"[Allintos] Inserting {len(records)} records into Allintos DB...")
    conn_str = db_url.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    try:
        for i, rec in enumerate(records):
            if is_kurumsal_bilgi(rec):
                continue
            mesaj = rec["mesaj"]
            cevap = rec.get("cevap")
            if not cevap or not str(cevap).strip():
                raise ValueError(f"Kayit icin gecerli bir 'cevap' bulunamadi: {rec}")

            sektor = rec["beklenen_sektor"]
            is_augmented = rec.get("is_augmented", False)
            emb_str = "[" + ",".join(map(str, dense_rows[i].tolist())) + "]"
            intent_id = resolve_intent_id_for_sector(sektor)
            if intent_id is None:
                raise ValueError(
                    f"Allintos intents tablosunda sektor={sektor!r} icin intent_id bulunamadi."
                )

            cur.execute(
                """
                INSERT INTO qa_embeddings (intent_id, question, answer, embedding, is_augmented, created_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (intent_id, mesaj, cevap, emb_str, is_augmented),
            )
        conn.commit()
        print("[Allintos] Sync complete.")
    except Exception as exc:
        conn.rollback()
        print(f"[Allintos] Failed to insert records: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


def _append_npz_index(
    paths: dict[str, Path],
    new_texts: list[str],
    new_meta: list[dict],
    new_dense: np.ndarray,
    new_sparse: list[dict[str, float]],
) -> int:
    print("[IndexSync] NPZ append basliyor (mevcut index yukleniyor)...", flush=True)
    vectors, texts, meta, sparse_vectors = _load_index_bundle(paths)
    print(f"[IndexSync] Mevcut index yuklendi: {vectors.shape[0]} satir", flush=True)

    merged_vectors = np.vstack([vectors, new_dense.astype(np.float32)])
    texts.extend(new_texts)
    meta.extend(new_meta)
    sparse_vectors.extend(new_sparse)

    _assert_index_consistency(merged_vectors, texts, meta, sparse_vectors)

    payload = {"texts": texts, "meta": meta, "sparse_vectors": sparse_vectors}
    print(
        f"[IndexSync] NPZ yaziliyor ({merged_vectors.shape[0]} satir, "
        f"~{merged_vectors.nbytes // (1024*1024)} MB)...",
        flush=True,
    )
    _atomic_save_npz(paths["vectors"], merged_vectors)
    print("[IndexSync] NPZ yazildi.", flush=True)

    print("[IndexSync] index_meta.json yaziliyor...", flush=True)
    _atomic_save_json(paths["metadata"], payload)
    print("[IndexSync] index_meta.json yazildi.", flush=True)

    print(
        f"[IndexSync] NPZ append tamamlandi: +{len(new_texts)} satir, "
        f"toplam={merged_vectors.shape[0]}",
        flush=True,
    )
    return merged_vectors.shape[0]


def _upsert_pgvector(
    records: list[dict],
    new_texts: list[str],
    new_meta: list[dict],
    new_dense: np.ndarray,
) -> int:
    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        m = new_meta[i]
        raw_sec = str(m.get("beklenen_sektor") or "ood")
        kayit_tipi = m.get("kayit_tipi") or infer_kayit_tipi_legacy(rec)
        rows.append(
            {
                "source_id": source_id_for_record(rec),
                "sector": normalize_pg_sector(raw_sec, kayit_tipi=kayit_tipi),
                "sub_intent": m.get("intent_code", "none"),
                "text_content": new_texts[i],
                "embedding": new_dense[i],
                "lang": m.get("lang", "tr"),
                "meta": m,
            }
        )

    store = VectorIndexStore(auto_migrate=True)
    print(f"[IndexSync] pgvector upsert basliyor ({len(rows)} satir)...", flush=True)
    n = store.upsert_batch(rows)
    print(f"[IndexSync] pgvector upsert tamamlandi: {n} satir", flush=True)
    return n


def sync_new_qa_records(new_records: list[dict]) -> None:
    """
    Admin add_qa sonrasi: Allintos (opsiyonel) + NPZ append + pgvector upsert.
    Process-level lock ile korunur.
    """
    if not new_records:
        return

    t0 = time.perf_counter()
    with _sync_lock:
        print(f"[IndexSync] Incremental sync basliyor ({len(new_records)} kayit)...", flush=True)
        paths = active_paths()
        _assert_no_source_id_collisions(new_records, paths)
        texts, meta, dense, sparse = encode_new_records(new_records)
        encode_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        _sync_allintos(new_records, dense)
        allintos_ms = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        total_rows = _append_npz_index(paths, texts, meta, dense, sparse)
        npz_ms = (time.perf_counter() - t2) * 1000

        t3 = time.perf_counter()
        _upsert_pgvector(new_records, texts, meta, dense)
        pg_ms = (time.perf_counter() - t3) * 1000

        reset_embedder()

        elapsed = time.perf_counter() - t0
        print(
            f"[IndexSync] Incremental sync tamamlandi: toplam={total_rows} satir, "
            f"{elapsed:.2f}s "
            f"(encode={encode_ms:.0f}ms allintos={allintos_ms:.0f}ms "
            f"npz={npz_ms:.0f}ms pg={pg_ms:.0f}ms)",
            flush=True,
        )


def remove_records_from_index(source_ids: list[str]) -> None:
    """Incremental silme — NPZ/meta filtre + pgvector DELETE."""
    if not source_ids:
        return

    ids = {str(s) for s in source_ids}
    with _sync_lock:
        paths = active_paths()
        vectors, texts, meta, sparse_vectors = _load_index_bundle(paths)

        keep_mask = []
        for i, m in enumerate(meta):
            sid = str(m.get("source_id") or m.get("id") or f"gen_{i}")
            keep_mask.append(sid not in ids)

        if all(keep_mask):
            print(f"[IndexSync] Silinecek source_id bulunamadi: {ids}")
            return

        removed = len(keep_mask) - sum(keep_mask)
        mask = np.array(keep_mask, dtype=bool)
        new_vectors = vectors[mask]
        new_texts = [t for t, k in zip(texts, keep_mask) if k]
        new_meta = [m for m, k in zip(meta, keep_mask) if k]
        new_sparse = [s for s, k in zip(sparse_vectors, keep_mask) if k]

        _assert_index_consistency(new_vectors, new_texts, new_meta, new_sparse)
        _atomic_save_npz(paths["vectors"], new_vectors)
        _atomic_save_json(
            paths["metadata"],
            {"texts": new_texts, "meta": new_meta, "sparse_vectors": new_sparse},
        )

        from sqlalchemy import text as sql_text
        from app.db.connection import get_engine
        from app.db.schema import TABLE_NAME

        eng = get_engine()
        with eng.begin() as conn:
            for sid in ids:
                conn.execute(
                    sql_text(f"DELETE FROM {TABLE_NAME} WHERE source_id = :sid"),
                    {"sid": sid},
                )

        reset_embedder()
        print(f"[IndexSync] Silindi: {removed} satir (source_ids={ids})")


# Geriye dönük / admin_qa isimlendirme
background_sync_index_incremental = sync_new_qa_records
