# -*- coding: utf-8 -*-
"""Transfer Learning Check — görülmemiş hibrit senaryo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, _normalize

GIRDI = (
    "Sürekli toplantı yapıp p!zza yemekten sıkıldık, "
    "n0'olur b!z!m s!ber-güvenl!k altyapısındaki `savunma` kalkanlarını "
    "güncelleyecek bir partner bulalım, dünkü siber saldırı çok kötüydü."
)


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    norm = _normalize(GIRDI)
    y = bot.sor(GIRDI)

    print("=" * 70)
    print("TRANSFER LEARNING CHECK")
    print("=" * 70)
    print(f"GIRDI    : {GIRDI}")
    print(f"NORMALIZE: {norm}")
    print(f"TEMIZ    : {y.temiz_sorgu!r}")
    print(f"BACKEND  : {y.rewrite_backend}")
    print(f"SEKTOR   : {y.sektor}")
    print(f"YONTEM   : {y.yontem}")
    print(f"SKOR     : {y.skor:.3f}")
    print(f"MOD      : {y.mod}")
    print(f"ACIKLAMA : {y.aciklama}")
    print("-" * 70)

    checks = {
        "leet_pizza": "pizza" in norm and "p!zza" not in norm,
        "leet_siber": "siber" in norm and "s!ber" not in norm,
        "leet_bizim": "bizim" in norm,
        "no_askeri": y.sektor != "savunma",
        "hedef_bilisim": y.sektor == "bilişim",
    }
    for k, v in checks.items():
        print(f"  {'✓' if v else '✗'} {k}")

    ok = checks["hedef_bilisim"] and checks["no_askeri"]
    print("=" * 70)
    print("SONUC:", "PASS — mantık genelledi (bilişim)" if ok else f"FAIL — {y.sektor}")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
