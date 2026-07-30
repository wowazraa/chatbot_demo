"""Held-out paraphrase testi — teaching seed'lerdeki birebir cümleler YOK.

Amaç: 35/35 overfitting mi, yoksa sektör semantiği mi öğrenildi?
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import MIN_BGE, Chatbot
from src.embedder import reset_embedder

# Kasıtlı olarak seed metinlerinden farklı yazım / eş anlamlı
HELD_OUT = [
    # sağlık
    ("Tomografi raporumu hekime göndermek istiyorum", "sağlık"),
    ("Dişim çok ağrıyor, bugün bakabilirler mi", "sağlık"),
    ("Hemogram için randevu oluşturmak istiyorum", "sağlık"),
    ("Laboratuvar sonuçlarım e-nabıza düşmedi", "sağlık"),
    ("Kırık şüphesiyle ortopediye gitmem lazım", "sağlık"),
    ("Ameliyattan önce anestezi doktoru bilgilendirecek mi", "sağlık"),
    ("Kronik ilaç raporum bitmek üzere yenilemem gerek", "sağlık"),
    ("Yoğun bakımdaki yakınımı hangi saatlerde görebilirim", "sağlık"),
    ("Başım dönüyor ve bulantım var hangi branşa gitmeliyim", "sağlık"),
    # turizm
    ("Nevşehir'de sıcak hava balonu turunun ücreti ne kadar", "turizm"),
    ("Otele öğleden önce giriş yapabilir miyiz", "turizm"),
    ("Her şey dahil tesis arıyorum Antalya civarı", "turizm"),
    ("İskele civarında butik pansiyon bakıyorum", "turizm"),
    ("Satın aldığım turun iptal ve iade kuralları neler", "turizm"),
    ("Rehber eşliğinde şehir gezisi ayarlamak istiyorum", "turizm"),
    ("Konaklama paketinde airport transfer var mı", "turizm"),
    ("İki kişilik hafta sonu için iptal edilebilir rezervasyon", "turizm"),
    # savunma
    ("Drone yer istasyonu yazılım mimarisi hakkında bilgi alabilir miyim", "savunma"),
    ("Muharebe alanında kriptolu veri iletimi nasıl yapılır", "savunma"),
    ("Elektronik harp spektrum kontrolü için çözüm arıyoruz", "savunma"),
    ("Zırhlı platformlarda predictive maintenance yazılımı lazım", "savunma"),
    ("C2 merkezinde common operating picture ekranı istiyoruz", "savunma"),
    ("İnsansız hava aracında çoklu sensör birleştirme entegrasyonu", "savunma"),
    ("SATCOM terminal bakım planı yönetim sistemi", "savunma"),
    ("Askeri lojistik deposunda stok takip yazılımı", "savunma"),
    # eğitim
    ("Başka üniversiteden yatay geçiş için tarihler nedir", "eğitim"),
    ("Diplomamı / mezuniyet belgemı nasıl talep ederim", "eğitim"),
    ("Online derslere kayıt dönemi açıldı mı", "eğitim"),
    ("Burs için hangi evrakları hazırlamam gerekiyor", "eğitim"),
    ("Not dökümümü (transkript) istiyorum", "eğitim"),
    ("Yüksek lisans programlarında boş kontenjan var mı", "eğitim"),
    ("Kampüs kartımı kaybettim yenilemek istiyorum", "eğitim"),
    ("Zorunlu staj için başvuru ekranı nerede", "eğitim"),
    ("Yaz döneminde ders kaydı ve harç ne kadar", "eğitim"),
    # belirsiz
    ("Selam, günün nasıl geçiyor", "belirsiz"),
    ("Sağ ol, yardımcı oldun", "belirsiz"),
    ("Bugün yağmur yağar mı", "belirsiz"),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"HELD-OUT | MIN_BGE={MIN_BGE} | corpus={bot.corpus_boyutu()}")
    ok = 0
    fail = []
    for i, (q, exp) in enumerate(HELD_OUT, 1):
        r = bot.sor(q, session_id=f"hold-{i}")
        if exp == "belirsiz":
            good = r.mod == "FB"
        else:
            good = (
                r.sektor == exp
                and r.mod in ("K1", "K2")
                and (r.yontem == "kisaltma" or (r.skor or 0) >= MIN_BGE)
            )
        mark = "OK" if good else "FAIL"
        if good:
            ok += 1
        else:
            fail.append((q, exp, r.sektor, r.mod, r.yontem, round(float(r.skor or 0), 3)))
        print(
            f"{mark} exp={exp:8} got={r.sektor}/{r.mod}/{r.yontem} "
            f"skor={float(r.skor or 0):.3f} | {q[:58]}"
        )
    print("-" * 60)
    print(f"Sonuc: {ok}/{len(HELD_OUT)}")
    if fail:
        print("\nFAIL:")
        for row in fail:
            print(" ", row)


if __name__ == "__main__":
    main()
