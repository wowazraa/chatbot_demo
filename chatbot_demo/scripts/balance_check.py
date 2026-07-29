"""
Niyet Dagilimi ve Dengesizlik (Imbalance) Analizi
=================================================
Hangi niyet/sektorden kac kayit var? Az ornekli siniflari yakala.

Ornekler:
    python scripts/balance_check.py
    python scripts/balance_check.py --input data/processed/chatbot_dataset_augmented.json
    python scripts/balance_check.py --input data.csv --intent_col niyet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

INTENT_ALIASES = ["beklenen_sektor", "niyet", "intent", "sektor", "label"]


def _load_frame(path: Path, intent_col: str) -> pd.DataFrame:
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

    if intent_col not in df.columns:
        for a in INTENT_ALIASES:
            if a in df.columns:
                df = df.rename(columns={a: intent_col})
                break

    if intent_col not in df.columns:
        raise KeyError(
            f"Kolon yok: {intent_col!r}. Mevcut: {list(df.columns)}"
        )
    return df


def run_balance_check(
    file_path: str | Path,
    intent_col: str,
    min_ratio: float = 0.01,
    min_count: int | None = None,
) -> None:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = _load_frame(path, intent_col)
    total = len(df)
    if total == 0:
        print("\n[STEP 2] NİYET DAĞILIMI — dosya bos")
        return

    # Bos / NaN etiketleri gorunur tut
    series = df[intent_col].fillna("(bos)").astype(str).str.strip()
    series = series.replace({"": "(bos)", "nan": "(bos)", "None": "(bos)"})

    counts = series.value_counts()
    percentages = series.value_counts(normalize=True) * 100
    report = pd.DataFrame({"Kayit Sayisi": counts, "Oran (%)": percentages.round(2)})

    print("\n[STEP 2] NİYET DAĞILIMI VE HASSASİYET RAPORU")
    print("-" * 50)
    print(f"Dosya       : {path}")
    print(f"Toplam      : {total}")
    print(f"Sinif sayisi: {len(counts)}")
    print("-" * 50)
    print(report.to_string())
    print("-" * 50)

    # Dengesizlik metrikleri
    max_c = int(counts.max())
    min_c = int(counts.min())
    imbalance_ratio = (max_c / max(min_c, 1)) if len(counts) else 0.0
    print(f"En cok / en az : {max_c} / {min_c}")
    print(f"Imbalance oranı: {imbalance_ratio:.1f}x  (max/min)")

    threshold = max(int(total * min_ratio), min_count or 0)
    low_samples = counts[counts < threshold]
    print("-" * 50)
    if not low_samples.empty:
        print(
            f"KRITIK UYARI: Asagidaki niyetlerde veri az "
            f"(esik < {threshold} kayit = %{min_ratio * 100:.1f}):"
        )
        for intent, count in low_samples.items():
            print(f"  - [{intent}]: Sadece {count} kayit var!")
    else:
        print("Veri dagilimi dengeli gorunuyor, kritik eksik sinif yok.")
    print("-" * 50)

    # Egitim ipucu: (bos)/belirsiz ayri tut
    if "(bos)" in counts.index or "belirsiz" in counts.index:
        bos = int(counts.get("(bos)", 0) + counts.get("belirsiz", 0))
        print(
            f"Not: Etiketsiz/belirsiz {bos} kayit — "
            f"egitimde ayri sinif veya filtre olarak degerlendir."
        )
        print("-" * 50)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Niyet dagilimi / imbalance analizi")
    ap.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="CSV veya JSON yol (varsayilan: augmented dataset)",
    )
    ap.add_argument(
        "--intent_col",
        default="beklenen_sektor",
        help="Niyet kolonu (CSV: niyet)",
    )
    ap.add_argument(
        "--min_ratio",
        type=float,
        default=0.01,
        help="Kritik az ornek esigi (toplamin orani, varsayilan 0.01)",
    )
    args = ap.parse_args()
    run_balance_check(args.input, args.intent_col, min_ratio=args.min_ratio)


if __name__ == "__main__":
    main()
