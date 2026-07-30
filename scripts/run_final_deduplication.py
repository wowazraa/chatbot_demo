"""
Faz 1 — Anlamsal Tekillestirme (Semantic Deduplication)
=======================================================
8470 kayitlik augmented corpus'ta BGE-M3 cosine > esik olan
mukerrerleri eleyip temiz JSON yazar.

Varsayilan: mevcut embeddings.npz (hizli, ayni BGE-M3 vektorleri).
Canli encode: --reencode

Ornekler:
    python scripts/run_final_deduplication.py --dry-run
    python scripts/run_final_deduplication.py
    python scripts/run_final_deduplication.py --threshold 0.92 --reencode
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
DEFAULT_NPZ = ROOT / "data" / "processed" / "embeddings.npz"
DEFAULT_META = ROOT / "data" / "processed" / "index_meta.json"


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, 1e-12)


def _load_dataset(path: Path, text_col: str) -> tuple[dict, list[dict], list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "kayitlar" in raw:
        meta = raw.get("meta", {})
        records = list(raw["kayitlar"])
    elif isinstance(raw, list):
        meta = {}
        records = list(raw)
    else:
        raise ValueError("JSON: {'kayitlar': [...]} veya liste bekleniyor.")

    # kolon alias
    if records and text_col not in records[0]:
        for alt in ("mesaj", "text", "sorgu", "query", "ham_mesaj"):
            if alt in records[0]:
                text_col = alt
                break

    cleaned_records: list[dict] = []
    corpus: list[str] = []
    for r in records:
        t = r.get(text_col)
        if t is None:
            continue
        s = str(t).strip()
        if not s:
            continue
        cleaned_records.append(r)
        corpus.append(s)

    return meta, cleaned_records, corpus


def _embeddings_from_npz(
    n_expected: int, corpus: list[str]
) -> np.ndarray | None:
    if not DEFAULT_NPZ.exists() or not DEFAULT_META.exists():
        return None
    vecs = np.load(DEFAULT_NPZ)["vectors"].astype(np.float32)
    meta = json.loads(DEFAULT_META.read_text(encoding="utf-8"))
    texts: list[str] = meta["texts"]
    if len(vecs) != n_expected or len(texts) != n_expected:
        print(
            f"  [!] Index boyutu uyusmuyor "
            f"(npz={len(vecs)}, meta={len(texts)}, data={n_expected}) "
            f"-> reencode gerekir.",
            flush=True,
        )
        return None
    # hizli eslesme kontrolu
    if texts[0] != corpus[0] or texts[-1] != corpus[-1]:
        print("  [!] Index metinleri dataset ile hizali degil -> reencode.", flush=True)
        return None
    print(f"  [+] embeddings.npz kullaniliyor ({vecs.shape})", flush=True)
    return _l2(vecs)


def _encode_bge(corpus: list[str], batch_size: int = 64) -> np.ndarray:
    print(
        f"  [-] BGE-M3 canli encode: {len(corpus)} cumle "
        f"(1-3 dk surebilir)...",
        flush=True,
    )
    try:
        from FlagEmbedding import BGEM3FlagModel

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
        out = model.encode(
            corpus,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=False,
        )
        return _l2(np.asarray(out["dense_vecs"], dtype=np.float32))
    except Exception as exc1:
        print(f"  [!] FlagEmbedding: {exc1}", flush=True)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("BAAI/bge-m3")
    emb = model.encode(
        corpus,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(emb, dtype=np.float32)


def _find_duplicates(embeddings: np.ndarray, threshold: float) -> set[int]:
    """Greedy: ilk gorunen kalir, benzer sonrakiler elenir."""
    n = embeddings.shape[0]
    print(
        f"  [-] Cosine tarama: n={n}, esik={threshold} "
        f"(matris ~{n * n * 4 / 1e6:.0f} MB)...",
        flush=True,
    )
    # Parca parca satir carpimi — bellek guvenli
    to_remove: set[int] = set()
    chunk = 256
    for start in range(0, n, chunk):
        end = min(start + chunk, n)
        block = embeddings[start:end] @ embeddings.T  # (chunk, n)
        for local_i, i in enumerate(range(start, end)):
            if i in to_remove:
                continue
            row = block[local_i]
            # i'den sonraki benzerler
            hits = np.where(row[i + 1 :] > threshold)[0] + (i + 1)
            for j in hits.tolist():
                if j not in to_remove:
                    to_remove.add(j)
        if start % (chunk * 8) == 0:
            print(f"  ... tarama {end}/{n} | aday elenen={len(to_remove)}", flush=True)
    return to_remove


def execute_final_clean(
    input_path: str | Path,
    output_path: str | Path,
    text_col: str = "mesaj",
    intent_col: str = "beklenen_sektor",
    threshold: float = 0.92,
    reencode: bool = False,
    dry_run: bool = False,
    batch_size: int = 64,
) -> dict:
    start_time = time.time()
    print("=" * 60, flush=True)
    print("FAZ 1: ANLAMSAL TEKILLESTIRME (SEMANTIC DEDUPLICATION)", flush=True)
    print("=" * 60, flush=True)

    input_path = Path(input_path)
    output_path = Path(output_path)
    meta, records, corpus = _load_dataset(input_path, text_col)
    n0 = len(records)
    print(f"[+] Veri yuklendi: {n0} satir | text_col={text_col}", flush=True)
    _ = intent_col  # rapor icin tutuluyor; filtre metin bazli

    if reencode:
        embeddings = _encode_bge(corpus, batch_size=batch_size)
    else:
        embeddings = _embeddings_from_npz(n0, corpus)
        if embeddings is None:
            print("  [!] npz kullanilamadi, canli encode...", flush=True)
            embeddings = _encode_bge(corpus, batch_size=batch_size)

    to_remove = _find_duplicates(embeddings, threshold)
    keep_idx = [i for i in range(n0) if i not in to_remove]
    cleaned = [records[i] for i in keep_idx]

    # sektor ozeti
    from collections import Counter

    before = Counter(
        str(r.get(intent_col) or "(bos)") for r in records
    )
    after = Counter(str(r.get(intent_col) or "(bos)") for r in cleaned)

    print(f"[+] Analiz bitti: {len(to_remove)} mukerrer elenecek.", flush=True)
    print("-" * 60, flush=True)
    print(f"Orijinal : {n0}", flush=True)
    print(f"Temiz    : {len(cleaned)}", flush=True)
    print(f"Silinen  : {len(to_remove)} ({100 * len(to_remove) / max(n0, 1):.1f}%)", flush=True)
    print("Sektor once -> sonra:", flush=True)
    for k in sorted(set(before) | set(after), key=lambda x: -before.get(x, 0)):
        print(f"  {k:<12} {before.get(k, 0):>5} -> {after.get(k, 0):>5}", flush=True)

    out_obj = {
        "meta": {
            **(deepcopy(meta) if isinstance(meta, dict) else {}),
            "dedup": {
                "source": str(input_path),
                "threshold": threshold,
                "method": "bge-m3-cosine-greedy",
                "original_count": n0,
                "removed_count": len(to_remove),
                "clean_count": len(cleaned),
                "reencode": reencode,
            },
        },
        "kayitlar": cleaned,
    }

    if dry_run:
        print("-" * 60, flush=True)
        print("[DRY-RUN] Dosya yazilmadi.", flush=True)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(out_obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("-" * 60, flush=True)
        print(f"[+] Kaydedildi: {output_path}", flush=True)

    elapsed = (time.time() - start_time) / 60.0
    print(f"Sure: {elapsed:.2f} dk", flush=True)
    print("=" * 60, flush=True)
    return out_obj["meta"]["dedup"]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Faz 1 semantik deduplication")
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--text_col", default="mesaj")
    ap.add_argument("--intent_col", default="beklenen_sektor")
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--reencode", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch_size", type=int, default=64)
    args = ap.parse_args()

    execute_final_clean(
        input_path=args.input,
        output_path=args.output,
        text_col=args.text_col,
        intent_col=args.intent_col,
        threshold=args.threshold,
        reencode=args.reencode,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
