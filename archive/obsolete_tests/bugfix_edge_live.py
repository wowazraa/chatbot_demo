# -*- coding: utf-8 -*-
"""
Bugfix kanıtı — Azra canlı demo edge-case'leri
================================================
SADECE iki cümle:
  1) siber + savunma → bilişim (askeri savunma değil)
  2) leet e-t!caret + kahve gürültüsü → e_ticaret (sağlık değil)

Kullanım:
    python tests/bugfix_edge_live.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, _normalize  # noqa: E402


CASES = [
    {
        "id": "E1_siber_savunma",
        "girdi": (
            "Şirketimizin sunucularına yönelik siber saldırılara karşı "
            "son derece sağlıklı bir savunma hattı kurmak istiyoruz."
        ),
        "beklenen": "bilişim",
        "yasak": ("savunma", "sağlık"),
    },
    {
        "id": "E2_leet_eticaret",
        "girdi": (
            "Toplantı çok yoğundu, kahveler soğudu, her neyse "
            "b!z!m e-t!caret s!tes!n!n sepet entegrasyonunu yapacak bir modül lazım."
        ),
        "beklenen": "e_ticaret",
        "yasak": ("sağlık", "turizm"),
    },
]


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    print("=" * 70)
    print("BUGFIX EDGE LIVE — kanıt koşusu")
    print(f"Rewriter={bot._rewriter.mode} | Corpus={bot.corpus_boyutu()}")
    print("=" * 70)

    fails = 0
    for case in CASES:
        g = case["girdi"]
        norm = _normalize(g)
        y = bot.sor(g)
        ok = y.sektor == case["beklenen"] and y.sektor not in case["yasak"]
        tag = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1

        print(f"\n[{tag}] {case['id']}")
        print(f"  girdi     : {g}")
        print(f"  normalize : {norm}")
        print(f"  temiz     : {y.temiz_sorgu!r}  (backend={y.rewrite_backend})")
        print(f"  sonuç     : {y.sektor} / {y.yontem} / skor={y.skor:.3f}")
        print(f"  beklenen  : {case['beklenen']}  yasak={list(case['yasak'])}")
        print(f"  aciklama  : {y.aciklama[:160]}")

    print("\n" + "=" * 70)
    print(f"ÖZET: {len(CASES) - fails}/{len(CASES)} pass")
    print("=" * 70)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
