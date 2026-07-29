# -*- coding: utf-8 -*-
"""Strict-Mode final sınavı — 3 senaryo tek koşu."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import SMALL_TALK_FB_MSG, Chatbot


CASES = [
    {
        "id": "T1",
        "girdi": "Havalar nasıl?",
        "beklenen_mod": "FB",
        "beklenen_sektor": "belirsiz",
        "msg_icinde": "kurumsal",
        "label": "Genel Sohbet",
    },
    {
        "id": "T2",
        "girdi": "Merhaba, nasılsın?",
        "beklenen_mod": "FB",
        "beklenen_sektor": "belirsiz",
        "msg_icinde": "kurumsal",
        "label": "Genel Sohbet",
    },
    {
        "id": "T3",
        "girdi": "Kargo rotalarımızı optimize etmemiz lazım",
        "beklenen_mod": ("K1", "K2"),
        "beklenen_sektor": "lojistik",
        "min_skor": 0.82,
        "hedef_skor": 0.82,
    },
]


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    print("FB_MSG:", SMALL_TALK_FB_MSG)
    print("=" * 64)
    failed = 0
    for c in CASES:
        y = bot.sor(c["girdi"])
        ok = True
        reasons = []
        mods = c["beklenen_mod"]
        if isinstance(mods, str):
            mods = (mods,)
        if y.mod not in mods:
            ok = False
            reasons.append(f"mod={y.mod} ∉ {mods}")
        if y.sektor != c["beklenen_sektor"]:
            ok = False
            reasons.append(f"sektor={y.sektor}")
        if "msg_icinde" in c and c["msg_icinde"] not in (y.aciklama or ""):
            ok = False
            reasons.append("kurumsal FB mesajı yok")
        if c.get("label") and y.inspector_label != c["label"]:
            ok = False
            reasons.append(f"label={y.inspector_label!r}")
        if "min_skor" in c and y.skor < c["min_skor"]:
            ok = False
            reasons.append(f"skor={y.skor:.3f} < {c['min_skor']}")
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {c['id']} {c['girdi']!r}")
        print(f"       → {y.sektor}/{y.mod} @{y.skor:.3f} | {y.inspector_label!r}")
        print(f"       → {(y.aciklama or '')[:120]}")
        if reasons:
            print(f"       !! {reasons}")
        if c.get("hedef_skor") and ok:
            print(f"       (hedef güven ~{c['hedef_skor']}; gerçek {y.skor:.3f})")
        print("-" * 64)
    print("SONUÇ:", f"{3 - failed}/3 PASS" if failed else "3/3 PASS — FREEZE OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
