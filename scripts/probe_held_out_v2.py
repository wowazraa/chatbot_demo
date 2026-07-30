"""Held-out v2 — ne ilk probe ne held-out-v1 cümleleri; taze yazım."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import MIN_BGE, Chatbot
from src.embedder import reset_embedder

V2 = [
    ("Röntgen filmimi doktora ulaştırmak istiyorum", "sağlık"),
    ("Dişetim şişti, acil diş bakımı lazım", "sağlık"),
    ("Biyokimya tahlili için gün alabilir miyim", "sağlık"),
    ("Çocuk ortopedisine randevu istiyorum", "sağlık"),
    ("Sedasyon öncesi bilgilendirme yapılacak mı", "sağlık"),
    ("Başım ağrıyor kusuyorum hangi bölüme", "sağlık"),
    ("Göreme'de balon turu kaç TL", "turizm"),
    ("Sabah erken otele yerleşebilir miyiz", "turizm"),
    ("Side'de her şey dahil otel bakıyorum", "turizm"),
    ("Liman kenarı küçük otel / pansiyon", "turizm"),
    ("Turumu iptal edersem param iade olur mu", "turizm"),
    ("Otel + havalimanı transfer paketi var mı", "turizm"),
    ("SİHA yer kontrol yazılımı hakkında bilgi", "savunma"),
    ("Sahada şifreli haberleşme nasıl kurulur", "savunma"),
    ("Zırhlı araç için arıza tahmin yazılımı", "savunma"),
    ("Komuta yerinde ortak durum resmi ekranı", "savunma"),
    ("İHA'da radar ve kamera füzyonu", "savunma"),
    ("Askeri ambar stok yazılımı arıyoruz", "savunma"),
    ("Yatay geçiş kontenjan ve tarihleri", "eğitim"),
    ("Mezuniyet evrakımı nasıl alırım", "eğitim"),
    ("Öğrenci kartım kayıp, yenisi nasıl çıkar", "eğitim"),
    ("Staj dosyası başvurusunu nereden yaparım", "eğitim"),
    ("Uzaktan ders kaydı açıldı mı harç ne", "eğitim"),
    ("Merhaba", "belirsiz"),
    ("İyi akşamlar teşekkür ederim", "belirsiz"),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"HELD-OUT v2 | MIN_BGE={MIN_BGE} | corpus={bot.corpus_boyutu()}")
    ok = 0
    fail = []
    for i, (q, exp) in enumerate(V2, 1):
        r = bot.sor(q, session_id=f"v2-{i}")
        if exp == "belirsiz":
            good = r.mod == "FB"
        else:
            good = r.sektor == exp and r.mod in ("K1", "K2") and (
                r.yontem == "kisaltma" or (r.skor or 0) >= MIN_BGE
            )
        if good:
            ok += 1
        else:
            fail.append((q, exp, r.sektor, r.mod, round(float(r.skor or 0), 3)))
        print(
            f"{'OK' if good else 'FAIL'} exp={exp:8} got={r.sektor}/{r.mod} "
            f"skor={float(r.skor or 0):.3f} | {q}"
        )
    print("-" * 60)
    print(f"Sonuc: {ok}/{len(V2)}")
    for row in fail:
        print(" FAIL", row)


if __name__ == "__main__":
    main()
