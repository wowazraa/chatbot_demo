"""
Veri Kalitesi ve Kayip Analizi
==============================
CSV veya proje JSON dataset'i icin bos / etiketsiz / duplicate ozeti.

Ornekler:
    python scripts/quality_check.py
    python scripts/quality_check.py --input data/processed/chatbot_dataset_augmented.json
    python scripts/quality_check.py --input data.csv --text_col sorgu --intent_col niyet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"


def _load_frame(path: Path, text_col: str, intent_col: str) -> pd.DataFrame:
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

    # Proje alias: mesaj / beklenen_sektor
    aliases = {
        text_col: ["mesaj", "sorgu", "text", "query", "ham_mesaj"],
        intent_col: ["beklenen_sektor", "niyet", "intent", "sektor", "label"],
    }
    for wanted, alts in aliases.items():
        if wanted in df.columns:
            continue
        for a in alts:
            if a in df.columns:
                df = df.rename(columns={a: wanted})
                break

    missing = [c for c in (text_col, intent_col) if c not in df.columns]
    if missing:
        raise KeyError(
            f"Kolon(lar) yok: {missing}. Mevcut: {list(df.columns)}"
        )
    return df


def run_quality_check(file_path: str | Path, text_col: str, intent_col: str) -> None:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = _load_frame(path, text_col, intent_col)
    total = len(df)
    if total == 0:
        print("\n[STEP 1] VERİ KALİTE RAPORU — dosya bos")
        return

    text = df[text_col]
    intent = df[intent_col]

    null_text = int(text.isnull().sum())
    null_intent = int(intent.isnull().sum())

    # Bos / sadece bosluk metin
    text_str = text.fillna("").astype(str)
    blank_text = int((text_str.str.strip() == "").sum())

    # Etiketsiz: NaN, "", "belirsiz", "nan"
    intent_str = intent.fillna("").astype(str).str.strip().str.lower()
    unlabeled = int(
        intent_str.isin({"", "nan", "none", "null", "belirsiz", "unknown"}).sum()
    )

    exact_dups = int(text_str.duplicated().sum())
    # strip sonrasi duplicate (gürültüye daha duyarli)
    strip_dups = int(text_str.str.strip().duplicated().sum())

    word_counts = text_str[text_str.str.strip() != ""].apply(
        lambda x: len(x.split())
    )
    very_short = int((word_counts < 2).sum()) if len(word_counts) else 0

    print("\n[STEP 1] VERİ KALİTE RAPORU")
    print("-" * 40)
    print(f"Dosya              : {path}")
    print(f"Total Row Count    : {total}")
    print(f"Missing Text Rows  : {null_text} ({(null_text / total) * 100:.2f}%)")
    print(f"Blank Text Rows    : {blank_text} ({(blank_text / total) * 100:.2f}%)")
    print(f"Missing Intent Rows: {null_intent} ({(null_intent / total) * 100:.2f}%)")
    print(f"Unlabeled Intent   : {unlabeled} ({(unlabeled / total) * 100:.2f}%)")
    print(f"Exact Duplicates   : {exact_dups} ({(exact_dups / total) * 100:.2f}%)")
    print(f"Strip Duplicates   : {strip_dups} ({(strip_dups / total) * 100:.2f}%)")
    if len(word_counts):
        print(f"Avg Word Count     : {word_counts.mean():.1f} words")
        print(f"Min/Max Word Count : {word_counts.min()} / {word_counts.max()} words")
        print(f"Very Short (<2 w)  : {very_short} ({(very_short / total) * 100:.2f}%)")
    else:
        print("Avg Word Count     : n/a (metin yok)")
    print("-" * 40)

    # Intent / sektor dagilimi
    print("\n[STEP 2] INTENT / SEKTOR DAGILIMI")
    print("-" * 40)
    counts = intent.fillna("(bos)").astype(str).str.strip().value_counts()
    for label, cnt in counts.items():
        print(f"  {label:<16} {cnt:>6}  ({cnt / total * 100:5.1f}%)")
    print("-" * 40)

    # Cabuk kayip ozeti
    junk = blank_text + unlabeled  # kaba ust sinir; overlap olabilir
    usable = total - blank_text
    print("\n[STEP 3] KISA OZET")
    print("-" * 40)
    print(f"Bos/cop metin      : {blank_text}")
    print(f"Etiketsiz/belirsiz : {unlabeled}")
    print(f"Duplicate (exact)  : {exact_dups}")
    print(f"Analiz edilebilir  : {usable} / {total}")
    print("-" * 40)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Veri kalite ve kayip analizi")
    ap.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="CSV veya JSON yol (varsayilan: augmented dataset)",
    )
    ap.add_argument("--text_col", default="mesaj", help="Metin kolonu (CSV: sorgu)")
    ap.add_argument(
        "--intent_col", default="beklenen_sektor", help="Niyet kolonu (CSV: niyet)"
    )
    args = ap.parse_args()
    run_quality_check(args.input, args.text_col, args.intent_col)


if __name__ == "__main__":
    main()
