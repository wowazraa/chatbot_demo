"""
Faz 1 — Temiz Vektor Indeksi
============================
chatbot_dataset_clean.json (2195) -> BGE-M3 canli encode ->
  data/processed/chatbot_dataset_clean_embeddings.npz
  data/processed/chatbot_dataset_clean_index_meta.json

Calistir:
    python scripts/build_clean_index.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.embedder import BGEEmbedder

CLEAN_JSON = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
OUT_NPZ = ROOT / "data" / "processed" / "chatbot_dataset_clean_embeddings.npz"
OUT_META = ROOT / "data" / "processed" / "chatbot_dataset_clean_index_meta.json"


def load_clean_records(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Temiz dataset yok: {path}\n"
            "Once: python scripts/run_final_deduplication.py"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    recs = data.get("kayitlar", data) if isinstance(data, dict) else data
    print(f"[+] {len(recs)} kayit yuklendi: {path.name}", flush=True)
    return list(recs)


def build(input_path: Path, out_npz: Path, out_meta: Path) -> None:
    print("=" * 60, flush=True)
    print("  FAZ 1: TEMIZ BGE-M3 VEKTOR INDEKSI", flush=True)
    print("=" * 60, flush=True)

    records = load_clean_records(input_path)
    texts: list[str] = []
    meta: list[dict] = []
    for rec in records:
        msg = ""
        for f in ("mesaj", "message", "text", "input"):
            if isinstance(rec.get(f), str) and rec[f].strip():
                msg = rec[f].strip()
                break
        if not msg:
            continue
        texts.append(msg)
        meta.append(
            {
                "id": rec.get("id"),
                "source_id": rec.get("source_id"),
                "beklenen_sektor": rec.get(
                    "beklenen_sektor", rec.get("beklened_sektor", "belirsiz")
                ),
                "beklenen_mod": rec.get("beklenen_mod", rec.get("beklened_mod", "K1")),
                "lang": rec.get("lang", "tr"),
                "zorluk": rec.get("zorluk", ""),
                "varyant": rec.get("varyant", "duz"),
            }
        )

    print(f"[+] Embed edilecek: {len(texts)} metin", flush=True)
    print("[-] BGE-M3 yukleniyor + canli encode (birkaç dk)...", flush=True)

    embedder = BGEEmbedder()
    t0 = time.time()
    embedder.build_index(texts, meta, show_progress=True)
    elapsed = time.time() - t0
    print(f"[+] Encode tamam: {elapsed:.1f}s | shape={embedder._vectors.shape}", flush=True)

    # Ozel dosya adlariyla kaydet (canli embeddings.npz'i ezme)
    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_npz, vectors=embedder._vectors)

    sparse = []
    if embedder._sparse_vectors:
        for d in embedder._sparse_vectors:
            sparse.append({k: float(v) for k, v in d.items()})
    else:
        sparse = [{} for _ in texts]

    payload = {
        "texts": embedder._texts,
        "meta": embedder._meta,
        "sparse_vectors": sparse,
        "source": str(input_path),
        "n": len(texts),
        "dim": int(embedder._vectors.shape[1]),
    }
    out_meta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[+] NPZ  -> {out_npz}", flush=True)
    print(f"[+] META -> {out_meta}", flush=True)

    # Hizli dogrulama (index bellekte)
    print("\n--- Hizli Test ---", flush=True)
    for q in (
        "hastane yönetim sistemi",
        "otel rezervasyon yazılımı",
        "radar komuta kontrol",
        "OBS LMS öğrenci kayıt",
    ):
        res = embedder.find_top_k_hybrid(q, k=1, alpha=0.9)
        if res:
            r = res[0]
            print(
                f"  '{q}'\n"
                f"    -> [{r.metadata.get('beklenen_sektor')}] "
                f"{r.score:.4f} | {r.text[:60]}",
                flush=True,
            )

    # Boyut dogrulama
    loaded = np.load(out_npz)["vectors"]
    assert loaded.shape[0] == len(texts), "NPZ satir sayisi uyusmuyor!"
    print(f"\n[+] Dogrulama OK: {loaded.shape[0]} x {loaded.shape[1]}", flush=True)
    print("=" * 60, flush=True)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Temiz corpus BGE-M3 index builder")
    ap.add_argument("--input", default=str(CLEAN_JSON))
    ap.add_argument("--out-npz", default=str(OUT_NPZ))
    ap.add_argument("--out-meta", default=str(OUT_META))
    args = ap.parse_args()

    build(Path(args.input), Path(args.out_npz), Path(args.out_meta))


if __name__ == "__main__":
    main()
