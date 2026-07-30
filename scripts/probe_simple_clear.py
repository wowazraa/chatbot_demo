"""Basit & açık cümleler — emin olunması gereken tüketici dili."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import MIN_BGE, Chatbot
from src.embedder import reset_embedder

SIMPLE = [
    ("Diş ağrım var acil bakılmalı", "sağlık"),
    ("Kan tahlili randevusu istiyorum", "sağlık"),
    ("Tahlil sonuçlarım sistemde görünmüyor", "sağlık"),
    ("Kardiyoloji randevusu almak istiyorum", "sağlık"),
    ("Antalya'da denize sıfır otel bakıyorum", "turizm"),
    ("İki kişilik otel rezervasyonu yapmak istiyorum", "turizm"),
    ("Tur iptal şartları nedir", "turizm"),
    ("Askeri lojistik yazılımı hakkında bilgi", "savunma"),
    ("İHA radar entegrasyonu nedir", "savunma"),
    ("Yaz okulu harç ücreti ne kadar", "eğitim"),
    ("Transkript istiyorum", "eğitim"),
    ("Çift anadal başvuru şartları neler", "eğitim"),
    ("Merhaba", "belirsiz"),
    ("Teşekkürler", "belirsiz"),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"SIMPLE | MIN_BGE={MIN_BGE} margin={bot.MIN_MARGIN} | n={bot.corpus_boyutu()}")
    ok = 0
    for i, (q, exp) in enumerate(SIMPLE, 1):
        r = bot.sor(q, session_id=f"simple-{i}")
        if exp == "belirsiz":
            good = r.mod == "FB"
        else:
            good = r.sektor == exp and r.mod in ("K1", "K2")
        ok += int(good)
        print(
            f"{'OK' if good else 'FAIL'} exp={exp:8} got={r.sektor}/{r.mod} "
            f"skor={float(r.skor or 0):.3f} | {q}"
        )
    print(f"Sonuc: {ok}/{len(SIMPLE)}")


if __name__ == "__main__":
    main()
