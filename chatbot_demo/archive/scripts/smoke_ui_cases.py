"""
UI smoke — ogreten yol (MIN_BGE=0.80, anahtar sozluk yok).

    python scripts/smoke_ui_cases.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TORCH", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, MIN_BGE
from src.embedder import reset_embedder

# (query, expected_sektor|None, expected_mod|None, session_id)
# session_id ayniysa HAFIZA / pivot test edilir
CASES = [
    (
        "lütfen acil yardımcı olur musunuz hastane otomasyonunda hekim çalışma saatlerini düzenlememiz gerekiyor",
        "sağlık",
        "K2",
        "s1",
    ),
    (
        "Kardiyoloji polikliniğinden yarın sabah için randevu oluşturmak istiyorum.",
        "sağlık",
        "K1",
        "s2",
    ),
    (
        "Sürekli başım dönüyor ve midem bulanıyor, hangi bölüme gitmem lazım?",
        "sağlık",
        "K2",
        "s3",
    ),
    (
        "Tahlil sonuçlarım sisteme düşmüş mü kontrol edebilir misiniz?",
        "sağlık",
        "K2",
        "s4",
    ),
    (
        "Antalya'da her şey dahil, denize sıfır otel fiyatları nedir?",
        "turizm",
        "K1",
        "s5",
    ),
    (
        "Önümüzdeki hafta sonu için iki kişilik iptal edilebilir rezervasyon yapmak istiyorum.",
        "turizm",
        "K1",
        "s6",
    ),
    (
        "Müze kart geçerli olan tarihi yerlerin listesini alabilir miyim?",
        "turizm",
        "K1",
        "s7",
    ),
    # HAFIZA zehiri: once turizm, sonra savunma icerikli soru
    (
        "Antalya'da denize sıfır otel bakıyoruz",
        "turizm",
        "K1",
        "poison",
    ),
    (
        "Askeri lojistik yazılımlarında siber güvenlik protokolleri nasıl uygulanıyor?",
        "savunma",
        "K2",
        "poison",
    ),
    (
        "İnsansız kara araçlarının radar entegrasyonu hakkında bilgi alabilir miyim?",
        "savunma",
        "K2",
        "s8",
    ),
    (
        "Birlik içi güvenli haberleşme cihazlarının bakım periyotları nedir?",
        "savunma",
        "K2",
        "s9",
    ),
    (
        "Yaz okulu ders kayıtları ne zaman başlıyor ve harç ücreti ne kadar?",
        "eğitim",
        "K2",
        "s10",
    ),
    (
        "Çift anadal programına başvuru şartları ve taban puanları nelerdir?",
        "eğitim",
        "K2",
        "s11",
    ),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"MIN_BGE={MIN_BGE} | corpus={bot.corpus_boyutu()} | bge={bot.bge_aktif_mi()}")
    print("-" * 60)

    ok_n = graded = 0
    for i, (q, exp_sek, exp_mod, sid) in enumerate(CASES, 1):
        r = bot.sor(q, session_id=sid)
        graded += 1
        ok = r.sektor == exp_sek and r.mod == exp_mod
        if exp_mod == "K2" and r.yontem not in ("kisaltma", "bge-m3", "hafiza"):
            # K2 icin skor kontrolu
            if r.yontem == "bge-m3" and r.skor < MIN_BGE:
                ok = False
        if exp_mod == "K1" and r.yontem != "kisaltma":
            ok = False
        # HAFIZA beklenmiyor bu setde
        if r.mod == "HAFIZA" and exp_mod != "HAFIZA":
            ok = False
        mark = "OK" if ok else "FAIL"
        if ok:
            ok_n += 1
        print(
            f"{mark} [{i}] {r.sektor}/{r.mod}/{r.yontem} skor={r.skor:.3f} "
            f"(beklenen={exp_sek}/{exp_mod}) sid={sid}"
        )
        print(f"     Q: {q[:72]}")

    print("-" * 60)
    print(f"Sonuc: {ok_n}/{graded}")


if __name__ == "__main__":
    main()
