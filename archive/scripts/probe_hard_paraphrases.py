"""Zor paraphrase taraması — ezber yok, sadece skor/sektör ölçümü."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import MIN_BGE, Chatbot
from src.embedder import reset_embedder

PROBES = [
    # sağlık — semptom / süreç / tüketici
    ("MR sonucumu doktora iletmek istiyorum", "sağlık"),
    ("Diş ağrısı için acil muayene var mı", "sağlık"),
    ("Kan tahlili randevusu almak istiyorum", "sağlık"),
    ("E-nabızda laboratuvar sonuçlarım görünmüyor", "sağlık"),
    ("Ortopedi için sıraya girmek istiyorum", "sağlık"),
    ("Ameliyat öncesi anestezi bilgilendirmesi lazım", "sağlık"),
    ("İlaç raporumun yenilenmesi için ne yapmalıyım", "sağlık"),
    ("Yoğun bakım ziyaret saatleri nedir", "sağlık"),
    # turizm
    ("Kapadokya'da balon turu paket fiyatı nedir", "turizm"),
    ("Erken check-in ile oda ayırtabilir miyim", "turizm"),
    ("All inclusive tatil köyü önerir misiniz", "turizm"),
    ("Uçak + otel kombine paket bakıyorum", "turizm"),
    ("Bodrum marina yakınında pansiyon arıyorum", "turizm"),
    ("Tur iptal şartları nelerdir", "turizm"),
    ("Şehir turu için rehberli gezi var mı", "turizm"),
    ("Havalimanı transferi dahil mi", "turizm"),
    # savunma
    ("İHA yer kontrol istasyonu yazılımı hakkında bilgi", "savunma"),
    ("Taktik sahada güvenli veri aktarımı nasıl sağlanır", "savunma"),
    ("Elektronik harp sistemlerinde spektrum yönetimi", "savunma"),
    ("Zırhlı araçlar için arıza öngörü yazılımı", "savunma"),
    ("Komuta kontrol merkezinde durum farkındalığı ekranı", "savunma"),
    ("Askeri depo envanter takip sistemi arıyoruz", "savunma"),
    ("UAV sensör füzyonu entegrasyonu", "savunma"),
    ("Güvenli uydu haberleşme terminali bakımı", "savunma"),
    # eğitim
    ("Yatay geçiş başvurusu ne zaman açılıyor", "eğitim"),
    ("Mezuniyet belgesi nasıl alınır", "eğitim"),
    ("Uzaktan eğitim ders kayıtları başladı mı", "eğitim"),
    ("Burs başvurusu için gerekli belgeler neler", "eğitim"),
    ("Transkript talep etmek istiyorum", "eğitim"),
    ("Yüksek lisans kontenjanları açık mı", "eğitim"),
    ("Öğrenci kimlik kartı yenileme süreci", "eğitim"),
    ("Staj başvuru formu nereden doldurulur", "eğitim"),
    # belirsiz / küçük konuşma — FB beklenir
    ("Merhaba nasılsın", "belirsiz"),
    ("Teşekkürler", "belirsiz"),
    ("Hava nasıl", "belirsiz"),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"MIN_BGE={MIN_BGE} corpus={bot.corpus_boyutu()}")
    fail = []
    ok = 0
    for i, (q, exp) in enumerate(PROBES, 1):
        r = bot.sor(q, session_id=f"probe-{i}")
        if exp == "belirsiz":
            good = r.mod == "FB" or r.sektor in (None, "belirsiz", "")
            # bazı sistemler belirsiz yerine sektör döndürebilir — FB şart
            good = r.mod == "FB"
        else:
            good = r.sektor == exp and r.mod in ("K1", "K2") and (r.yontem == "kisaltma" or r.skor >= MIN_BGE)
        mark = "OK" if good else "FAIL"
        if good:
            ok += 1
        else:
            fail.append((q, exp, r.sektor, r.mod, r.yontem, round(r.skor or 0, 3)))
        print(f"{mark} exp={exp:8} got={r.sektor}/{r.mod}/{r.yontem} skor={r.skor:.3f} | {q[:60]}")
    print("-" * 60)
    print(f"Sonuc: {ok}/{len(PROBES)}")
    if fail:
        print("\nFAIL listesi:")
        for row in fail:
            print(" ", row)


if __name__ == "__main__":
    main()
