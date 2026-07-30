# -*- coding: utf-8 -*-
"""
K1 Hint Collector regresyonu.

Kural: K1 sektör ATAMAZ; yalnızca keyword ipuçları (hint_score ≤ 0.50) üretir.
Çoklu sektör hit'leri paralel ipucu olarak kalır.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import K1_MAX_CONFIDENCE, _kural_eslestir, _normalize

COKLU_IPUCU = [
    ("sağlıklı bir sigorta yönetim kliniği arıyoruz", {"sağlık", "finans"}),
    ("hastane randevu sistemi ve veritabanı performansı", {"sağlık", "bilişim"}),
    ("hem eğitim LMS hem savunma radar çözümü bakıyoruz", {"eğitim", "savunma"}),
    (
        "Hastane randevu sistemlerinde veritabanı yoğunluğu oluşuyor",
        {"sağlık", "bilişim"},
    ),
]

TEK_SEKTOR_IPUCU = [
    ("hastane yönetim sistemi arıyoruz", "sağlık"),
    ("otel rezervasyon sistemimizi yenilemek istiyoruz", "turizm"),
    ("komuta kontrol ve radar tehdit izleme", "savunma"),
    ("uzaktan eğitim ve LMS platformu", "eğitim"),
    ("sigorta poliçe yönetim sistemi", "finans"),
    ("personel bordro ve CRM yazılımı", "ik_kurumsal"),
]

SOFT_ONLY = [
    "sağlıklı bir iş ortaklığı kurmak istiyoruz",
    "eğitimli bir yaklaşım bekliyoruz",
]


def main() -> None:
    fail = 0

    print("--- Coklu sektor: paralel hints (atama yok) ---")
    for girdi, bek_set in COKLU_IPUCU:
        hints, acik = _kural_eslestir(_normalize(girdi))
        got = set(hints)
        ok = bek_set.issubset(got)
        for s, h in hints.items():
            if float(h["hint_score"]) > K1_MAX_CONFIDENCE:
                ok = False
        print(("OK " if ok else "X  "), f"bek subset {bek_set} got={got} | {girdi[:56]}")
        print(f"     {acik}")
        if not ok:
            fail += 1

    print("\n--- Tek sektor ipucu (atama degil) ---")
    for girdi, bek in TEK_SEKTOR_IPUCU:
        hints, acik = _kural_eslestir(_normalize(girdi))
        ok = bek in hints and all(
            float(h["hint_score"]) <= K1_MAX_CONFIDENCE for h in hints.values()
        )
        print(("OK " if ok else "X  "), f"bek={bek} in {set(hints)} | {girdi[:56]}")
        if not ok:
            fail += 1

    print("\n--- Soft-only: dusuk/hint veya yok ---")
    for girdi in SOFT_ONLY:
        hints, acik = _kural_eslestir(_normalize(girdi))
        # Soft-only hard_hits=0 olabilir; sektör ATAYamaz (bu fonksiyonda zaten yok)
        ok = all(int(h.get("hard_hits") or 0) == 0 for h in hints.values())
        print(("OK " if ok else "X  "), f"hints={set(hints)} | {girdi}")
        if not ok:
            fail += 1

    print("\n" + ("PASS" if fail == 0 else f"FAIL ({fail})"))
    raise SystemExit(fail)


if __name__ == "__main__":
    main()
