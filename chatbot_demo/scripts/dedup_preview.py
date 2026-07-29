"""
Semantik Deduplication On Izleme (Dry-Run)
==========================================
Tam corpus yerine kucuk sample ile BGE-M3 benzerlik taramasi.
Varsayilan: data/processed/embeddings.npz (hizli, model yukleme yok).
Istersen --reencode ile canli encode.

Ornekler:
    python scripts/dedup_preview.py
    python scripts/dedup_preview.py --sample_size 100
    python scripts/dedup_preview.py --reencode --sample_size 50
    python scripts/dedup_preview.py --input data.csv --text_col sorgu --sample_size 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Transformers'in TF/Keras 3 yoluna dusmesini engelle
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"
DEFAULT_NPZ = ROOT / "data" / "processed" / "embeddings.npz"
DEFAULT_META = ROOT / "data" / "processed" / "index_meta.json"

TEXT_ALIASES = ["mesaj", "sorgu", "text", "query", "ham_mesaj"]


def _load_frame(path: Path, text_col: str) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".csv":
        df = pd.read_csv(path)
    elif suf == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "kayitlar" in raw:
            df = pd.DataFrame(raw["kayitlar"])
        elif isinstance(raw, list):
            df = pd.DataFrame(raw)
        else:
            raise ValueError("JSON: liste veya {'kayitlar': [...]} bekleniyor.")
    else:
        raise ValueError(f"Desteklenmeyen format: {suf} (csv/json)")

    if text_col not in df.columns:
        for a in TEXT_ALIASES:
            if a in df.columns:
                df = df.rename(columns={a: text_col})
                break

    if text_col not in df.columns:
        raise KeyError(f"Kolon yok: {text_col!r}. Mevcut: {list(df.columns)}")
    return df


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, 1e-12)


def _encode_bge(texts: list[str]) -> np.ndarray:
    """Canli BGE-M3 dense encode (yavas; --reencode)."""
    try:
        from FlagEmbedding import BGEM3FlagModel

        print("  Model: FlagEmbedding BAAI/bge-m3 ...", flush=True)
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
        out = model.encode(texts, return_dense=True, return_sparse=False)
        return _l2(np.asarray(out["dense_vecs"], dtype=np.float32))
    except Exception as exc1:
        print(f"  [!] FlagEmbedding: {exc1}", flush=True)

    try:
        from sentence_transformers import SentenceTransformer

        print("  Model: sentence-transformers BAAI/bge-m3 ...", flush=True)
        model = SentenceTransformer("BAAI/bge-m3")
        emb = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return np.asarray(emb, dtype=np.float32)
    except Exception as exc2:
        raise RuntimeError(
            "BGE encode basarisiz. embeddings.npz ile calistir "
            "(--reencode olmadan) veya: pip install tf-keras FlagEmbedding"
        ) from exc2


def _from_project_index(
    sample_size: int, seed: int
) -> tuple[list[str], np.ndarray]:
    if not DEFAULT_NPZ.exists() or not DEFAULT_META.exists():
        raise FileNotFoundError(
            f"Index yok: {DEFAULT_NPZ}\nOnce: python scripts/build_index.py"
        )
    vecs = np.load(DEFAULT_NPZ)["vectors"].astype(np.float32)
    meta = json.loads(DEFAULT_META.read_text(encoding="utf-8"))
    texts: list[str] = meta["texts"]
    n_all = min(len(vecs), len(texts))
    n = min(sample_size, n_all)
    rng = np.random.default_rng(seed)
    idx = rng.choice(n_all, size=n, replace=False)
    idx.sort()
    corpus = [texts[i] for i in idx]
    emb = _l2(vecs[idx])
    print(
        f"  Kaynak: embeddings.npz | toplam={n_all} | sample={n}",
        flush=True,
    )
    return corpus, emb


def _print_pairs(
    corpus: list[str],
    cosine: np.ndarray,
    threshold: float,
    max_pairs: int,
) -> int:
    duplicates_found = 0
    shown = 0
    n = len(corpus)
    for i in range(n):
        for j in range(i + 1, n):
            score = float(cosine[i, j])
            if score > threshold:
                duplicates_found += 1
                if shown < max_pairs:
                    print(f"  Olasi kopya (sim={score:.4f}):", flush=True)
                    print(f"    1. {corpus[i]}", flush=True)
                    print(f"    2. {corpus[j]}", flush=True)
                    print("-" * 30, flush=True)
                    shown += 1
    if duplicates_found > shown:
        print(
            f"  ... +{duplicates_found - shown} cift daha "
            f"(--max_pairs ile artir)",
            flush=True,
        )
    return duplicates_found


def run_dedup_preview(
    file_path: str | Path,
    text_col: str,
    sample_size: int = 100,
    threshold: float = 0.90,
    max_pairs: int = 40,
    seed: int = 42,
    reencode: bool = False,
) -> None:
    print(
        f"\n[STEP 3] LOKAL BGE-M3 DEDUPLICATION ON IZLEME "
        f"(Sample: {sample_size}, esik={threshold})",
        flush=True,
    )
    print("-" * 60, flush=True)

    if reencode:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        print(f"Dosya: {path} | mod: canli encode", flush=True)
        df = _load_frame(path, text_col)
        df = df.dropna(subset=[text_col]).copy()
        df[text_col] = df[text_col].astype(str).str.strip()
        df = df[df[text_col] != ""]
        n_all = len(df)
        n = min(sample_size, n_all)
        df_sample = (
            df.sample(n=n, random_state=seed) if n < n_all else df.head(n)
        )
        corpus = df_sample[text_col].tolist()
        print(f"Corpus: {n_all} | sample: {n} | seed={seed}", flush=True)
        embeddings = _encode_bge(corpus)
    else:
        print("Dosya: embeddings.npz (proje index) | mod: dry-run hizli", flush=True)
        try:
            corpus, embeddings = _from_project_index(sample_size, seed)
        except FileNotFoundError:
            print("  [!] Index yok, --reencode yoluna dusuluyor...", flush=True)
            return run_dedup_preview(
                file_path,
                text_col,
                sample_size=sample_size,
                threshold=threshold,
                max_pairs=max_pairs,
                seed=seed,
                reencode=True,
            )

    cosine = embeddings @ embeddings.T
    n = len(corpus)
    print("-" * 60, flush=True)
    print("Benzer ciftler (dry-run, silme yok):", flush=True)
    duplicates_found = _print_pairs(corpus, cosine, threshold, max_pairs)

    pct = (duplicates_found / max(n * (n - 1) / 2, 1)) * 100
    print("-" * 60, flush=True)
    print(
        f"[OZET] {n} satirda {duplicates_found} semantik kopya adayi "
        f"(esik>{threshold}). Cift uzayi orani ~%{pct:.2f}.",
        flush=True,
    )
    print(
        "Not: Bu dry-run; veri silinmez. Canli encode: --reencode",
        flush=True,
    )
    print("-" * 60, flush=True)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="BGE-M3 semantik dedup on izleme")
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--text_col", default="mesaj")
    ap.add_argument("--sample_size", type=int, default=100)
    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--max_pairs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--reencode",
        action="store_true",
        help="embeddings.npz yerine canli BGE-M3 encode",
    )
    args = ap.parse_args()

    run_dedup_preview(
        args.input,
        args.text_col,
        sample_size=args.sample_size,
        threshold=args.threshold,
        max_pairs=args.max_pairs,
        seed=args.seed,
        reencode=args.reencode,
    )


if __name__ == "__main__":
    main()
