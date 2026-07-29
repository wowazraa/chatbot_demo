"""
GENELLEME / EZBER AYRIMI — Fresh held-out suite

Kurallar:
  - Önceki smoke / probe / teaching seed cümlelerini BİREBİR kullanma
  - Farklı kelime seçimi, farklı şehir/branş/ürün, farklı cümle yapıları
  - Hem net sektör hem bilerek belirsiz / tuzak vakalar

Çalıştır:
  python scripts/probe_generalization_fresh.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import MIN_BGE, Chatbot
from src.embedder import reset_embedder

# (soru, beklenen_sektor)  — beklenen "belirsiz" → FB şart
FRESH: list[tuple[str, str]] = [
    # ── sağlık (net, yeni yazım) ──
    ("Gözüm kızarık ve kaşınıyor, göz doktoruna mı gitmeliyim", "sağlık"),
    ("Kulak burun boğaz için sıra alabilir miyim", "sağlık"),
    ("Gebelik kontrol ultrasonuna gün vermenizi istiyorum", "sağlık"),
    ("Aşı kartımı sistemden sorgulayabilir misiniz", "sağlık"),
    ("Fizik tedavi seanslarım kaçta başlıyor", "sağlık"),
    ("Psikiyatri polikliniğine ilk kez başvuracağım ne yapmalıyım", "sağlık"),
    ("Recetem eczanede görünmüyor kontrol eder misiniz", "sağlık"),
    ("Acilde bekleyen yakınımın durumu hakkında bilgi alabilir miyim", "sağlık"),
    ("Mamografi çekimi için randevu istiyorum", "sağlık"),
    ("Diyabet kontrollerim için iç hastalıklarına yönlendirir misiniz", "sağlık"),
    ("Serum takılıyken ziyaretçi girebilir mi", "sağlık"),
    ("Ameliyat raporumu PDF olarak indirebilir miyim", "sağlık"),
    ("Alerji testine nasıl hazırlanmalıyım", "sağlık"),
    ("Bebeğimin aşı takviminde eksik var mı bakın", "sağlık"),
    ("Cildiye için online sıra sistemi çalışıyor mu", "sağlık"),
    # ── turizm (net, yeni yazım) ──
    ("Çeşme'de deniz manzaralı butik otel fiyatları", "turizm"),
    ("Uludağ kayak oteli paketleri ne kadar", "turizm"),
    ("Cruise gemisi Akdeniz turu rezervasyonu yapmak istiyorum", "turizm"),
    ("Airbnb tarzı günlük kiralık villa Antalya", "turizm"),
    ("Otogardan otele servis var mı bu pakette", "turizm"),
    ("Çocuklu aile için animasyonlu tatil köyü arıyorum", "turizm"),
    ("Erken rezervasyon indirimi bu sezon geçerli mi", "turizm"),
    ("Oda + kahvaltı mı yoksa yarım pansiyon mu daha uygun", "turizm"),
    ("Efes antik kenti turuna katılmak istiyorum", "turizm"),
    ("Valiz bırakma hizmeti otelde var mı", "turizm"),
    ("Son dakika yurtiçi tatil fırsatları neler", "turizm"),
    ("Çift kişilik deluxe oda müsaitlik tarihi", "turizm"),
    ("Transferli Kapadokya günübirlik tur bakıyorum", "turizm"),
    ("Spa dahil wellness otel önerisi lazım", "turizm"),
    ("İptal sigortası tur paketine eklenebilir mi", "turizm"),
    # ── savunma (net, yeni yazım) ──
    ("Denizaltı sonar veri işleme yazılımı hakkında bilgi", "savunma"),
    ("Sınır güvenliği için termal kamera entegrasyonu", "savunma"),
    ("Hava savunma radar ağı izleme konsolu arıyoruz", "savunma"),
    ("Askeri personel için görev çizelgeleme yazılımı", "savunma"),
    ("Mayın tespit robotu kontrol yazılımı lazım", "savunma"),
    ("Gemi köprüüstü navigasyon entegrasyonu", "savunma"),
    ("Taktik tabletlerde çevrimdışı harita çözümü", "savunma"),
    ("Silah sistemi ateş kontrol yazılımı güncellemesi", "savunma"),
    ("Askeri siber olay müdahale platformu", "savunma"),
    ("İnsansız deniz aracı (İDA) kumanda yazılımı", "savunma"),
    ("Muhimmat envanter takip otomasyonu", "savunma"),
    ("Gece görüş cihazı kalibrasyon yazılımı", "savunma"),
    ("Askeri havaalanı pist yönetim sistemi", "savunma"),
    ("Kriptolu telsiz frekans planlama aracı", "savunma"),
    ("Simülatör tabanlı pilot eğitim yazılımı (askeri)", "savunma"),
    # ── eğitim (net, yeni yazım) ──
    ("Erasmus başvuru tarihleri ne zaman", "eğitim"),
    ("Yazılı sınav not itiraz dilekçesi nasıl verilir", "eğitim"),
    ("Yurt başvurusu için gelir belgesi şart mı", "eğitim"),
    ("Tezsiz yüksek lisans ücretleri nedir", "eğitim"),
    ("Öğrenci belgesi e-devletten mi alınıyor", "eğitim"),
    ("Ders ekle-bırak dönemi ne zaman bitiyor", "eğitim"),
    ("Hazırlık sınıfı muafiyet sınavı var mı", "eğitim"),
    ("Fakülte değişikliği için taban puanlar", "eğitim"),
    ("Bitirme tezi teslim tarihi nedir", "eğitim"),
    ("Açıköğretim kayıt yenileme ücreti", "eğitim"),
    ("Öğrenci kulübü etkinlik izni nasıl alınır", "eğitim"),
    ("Yaz stajı sigorta girişini kim yapıyor", "eğitim"),
    ("Doktora yeterlilik sınavına başvuru", "eğitim"),
    ("Kütüphane kitap gecikme cezası ne kadar", "eğitim"),
    ("Yabancı dil hazırlık atlama şartları", "eğitim"),
    # ── bilerek belirsiz / smalltalk (FB) ──
    ("Bugün maç var mı", "belirsiz"),
    ("Kahve önerir misin", "belirsiz"),
    ("Saat kaç", "belirsiz"),
    ("Nasılsın bugün", "belirsiz"),
    ("Şarkı sözü yazar mısın", "belirsiz"),
    ("Matematik sorusu çöz", "belirsiz"),
    ("Hava durumu İstanbul", "belirsiz"),
    ("En yakın market nerede", "belirsiz"),
    # ── tuzak: sektör kelimesi yok / çapraz çağrışım (yine de net niyet) ──
    ("Gözlük numarası ölçümü için randevu", "sağlık"),  # optik/göz
    ("Odamızın deniz tarafına bakmasını istiyoruz", "turizm"),
    ("Birlik deposunda mühimmat sayımı yazılımı", "savunma"),
    ("Final notum sisteme işlenmemiş", "eğitim"),
    # ── tuzak: karışık / emin olunmamalı → FB tercih ──
    ("Hem hastane hem otel yazılımı satıyor musunuz", "belirsiz"),
    ("Eğitim mi savunma mı bilmiyorum karar veremedim", "belirsiz"),
    ("Sistem çöktü bir şeyler lazım", "belirsiz"),
    ("Fiyat listesi gönderin", "belirsiz"),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    print("=" * 72)
    print("  FRESH GENERALIZATION SUITE (ezber ≠ öğrenme)")
    print(f"  MIN_BGE={MIN_BGE} | margin={bot.MIN_MARGIN} | corpus={bot.corpus_boyutu()}")
    print(f"  Vakalar: {len(FRESH)}")
    print("=" * 72)

    ok = 0
    by_exp: dict[str, list[int]] = {}
    fails: list[tuple] = []

    for i, (q, exp) in enumerate(FRESH, 1):
        r = bot.sor(q, session_id=f"fresh-{i}")
        if exp == "belirsiz":
            good = r.mod == "FB"
        else:
            good = (
                r.sektor == exp
                and r.mod in ("K1", "K2")
                and (r.yontem == "kisaltma" or float(r.skor or 0) >= MIN_BGE)
            )
        by_exp.setdefault(exp, [0, 0])
        by_exp[exp][1] += 1
        if good:
            ok += 1
            by_exp[exp][0] += 1
        else:
            fails.append(
                (q, exp, r.sektor, r.mod, r.yontem, round(float(r.skor or 0), 3))
            )
        mark = "OK  " if good else "FAIL"
        print(
            f"{mark} [{i:02d}] exp={exp:8} got={str(r.sektor):8}/{r.mod:6} "
            f"skor={float(r.skor or 0):.3f} | {q[:55]}"
        )

    print("-" * 72)
    print(f"TOPLAM: {ok}/{len(FRESH)}  ({100.0 * ok / len(FRESH):.1f}%)")
    print("Sektör kırılımı:")
    for k, (a, b) in sorted(by_exp.items()):
        print(f"  {k:10} {a}/{b}")
    if fails:
        print(f"\nFAIL ({len(fails)}):")
        for row in fails:
            print(" ", row)
    print("\nYorum: Yüksek skor + yeni ifadeler → öğrenme; sadece eski cümleler OK → ezbere yakın.")


if __name__ == "__main__":
    main()
