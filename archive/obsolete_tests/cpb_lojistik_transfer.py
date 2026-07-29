# -*- coding: utf-8 -*-
"""
CPB transfer — S01 akrabası (görülmemiş lojistik cümle).
Motor ezber kontrolü: savunma kelimesi var ama vektör lojistik baskın olmalı.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot

GIRDI = (
    "Depomuzdaki paletlerin ve kamyonların rotasını optimize etmemiz lazım, "
    "savunma sanayii ile hiçbir işimiz yok."
)


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    emb = bot._get_embedder()
    y = bot.sor(GIRDI)
    # Orijinal (savunma kelimesi dahil) üzerinde centroid ölçümü
    _, aff, cpb = bot._contextual_probability_bias(emb, GIRDI.lower())
    print("=" * 70)
    print("CPB TRANSFER — lojistik vs savunma")
    print("=" * 70)
    print(f"GIRDI : {GIRDI}")
    print(f"CLEAN : {y.temiz_sorgu!r}")
    print(f"NORM  : {y.normalize_girdi!r}")
    print(f"SONUC : {y.sektor} / {y.mod} / {y.yontem} @ {y.skor:.3f}")
    print(f"ACIK  : {y.aciklama}")
    print(
        f"CPB   : loj={aff.get('lojistik', 0):.3f} "
        f"sav={aff.get('savunma', 0):.3f} tic={aff.get('ticari', 0):.3f}"
    )
    print(f"NOTE  : {cpb}")
    ok = y.sektor == "lojistik" and y.sektor != "savunma"
    print("-" * 70)
    print("PASS — vektör hiyerarşisi OK" if ok else f"FAIL — got {y.sektor}")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
