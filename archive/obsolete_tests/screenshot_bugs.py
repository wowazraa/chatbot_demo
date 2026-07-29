# -*- coding: utf-8 -*-
"""Screenshot bug reproduction — 6 cases."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot

CASES = [
    ("L1", "Lojistik yazılımları için teklif alacağım, ancak gıda veya tarım sektörüyle hiçbir alakamız yok, sadece kargo dağıtım rotaları", ["lojistik"], ["belirsiz"]),
    ("L2", "Ya bugün de hava ne kadar sıcak, neyse... bizim e-ticaret sitesindeki ödeme altyapısında (pos) 3D secure entegrasyonu neden sürekli hata veriyor, çok acil bakmamız lazım!", ["e_ticaret", "finans"], ["belirsiz"]),
    ("L3", "hastane randevu s!stemler!nde ver! tabanı y0ğunluğu olusuyor, crm entegrasyonunda hata alıyoruz", ["sağlık"], ["ik_kurumsal"]),
    ("L4", "Dün akşam izlediğim filmde ana karakter bir yazılımcıydı ama sadece kod yazıp duruyordu, hiç aksiyon yoktu. Sence film nasıldı", ["belirsiz"], ["ik_kurumsal", "bilişim"]),
    ("L5", "Bir askeri radar projemiz var, bunun lojistik stok takibini (savunma sanayii değil, tamamen ticari depo yönetimi) nasıl optimize ederiz?", ["lojistik"], ["ik_kurumsal", "savunma"]),
    ("L6", "Dijital pazarlama kampanyalarımız için finansal bütçe planlaması yapıyoruz, ROI hesaplamaları için bir dashboard tasarımı lazım.", ["finans", "e_ticaret", "ik_kurumsal"], ["eğitim"]),
]


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    sid = "bug-sess"
    fail = 0
    for i, (cid, girdi, ok, ban) in enumerate(CASES):
        # L4/L5 hafıza zehri için aynı session (L3 sonrası)
        session = sid if cid in ("L3", "L4", "L5") else None
        if cid == "L3":
            bot._sessions.clear()
        y = bot.sor(girdi, session_id=session)
        bad = y.sektor in ban or (ok and y.sektor not in ok)
        status = "FAIL" if bad else "PASS"
        if bad:
            fail += 1
        print(f"[{status}] {cid} → {y.sektor}/{y.mod} @{y.skor:.2f} {y.yontem}")
        print(f"       clean={y.temiz_sorgu!r}")
        print(f"       { (y.aciklama or '')[:140]}")
    print(f"\n{6-fail}/6 PASS")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
