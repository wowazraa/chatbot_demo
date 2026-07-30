"""
100 sorguluk kapsamli threshold tarama scripti.
"""
import sys, os, logging
logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

sys.path.insert(0, ".")
from src.embedder import get_embedder

# ── 100 Sorgu Test Seti ──────────────────────────────────────────────────────
# (sorgu, beklenen_etiket)  etiket: health | defense | education | tourism | ood
TEST_DATA = [
    # ── SAGLIK – 20 sorgu ──────────────────────────────────────────────────
    ("Hastane yönetim yazılımı arıyoruz", "health"),
    ("Klinik randevu otomasyonu hizmeti almak istiyoruz", "health"),
    ("Poliklinik iş akışı dijitalleştirme çözümü lazım", "health"),
    ("HBYS sistemimizi güncellemek istiyoruz", "health"),
    ("e-Nabız entegrasyonu yapacak yazılım gerekiyor", "health"),
    ("Hasta takip sistemi kurulumu için teklif istiyoruz", "health"),
    ("Tele-tıp altyapısı kurmak istiyoruz", "health"),
    ("Şirketimiz için klinik randevu otomasyonu kurmak istiyoruz", "health"),
    ("Ameliyathane yönetim yazılımı arıyoruz", "health"),
    ("Hekim takvim ve randevu sistemi entegrasyonu", "health"),
    ("Uzaktan sağlık asistanı yazılımı geliştirmek istiyoruz", "health"),
    ("AHBS entegrasyonu için yazılım hizmeti almak istiyoruz", "health"),
    ("Muayene yönetim sistemi kurulumu yapacak firma arıyoruz", "health"),
    ("Radyoloji departmanı için dijital görüntüleme yazılımı", "health"),
    ("Acil servis yönetimi yazılımı hizmeti almak istiyoruz", "health"),
    ("Tahlil ve laboratuvar takip sistemi arıyoruz", "health"),
    ("Hemşire iş akışı otomasyonu yazılımı", "health"),
    ("Ameliyathanelerdeki tıbbi cihazların bakım takip süreçlerini dijitalleştirmek", "health"),
    ("Kurumsal sağlık bilgi sistemi entegrasyonu lazım", "health"),
    ("Doktor program ve performans takip yazılımı", "health"),

    # ── SAVUNMA – 20 sorgu ─────────────────────────────────────────────────
    ("Radar veri analiz yazılımı hizmeti almak istiyoruz", "defense"),
    ("İnsansız hava aracı kontrol yazılımı gerekiyor", "defense"),
    ("Askeri haberleşme altyapısı güçlendirmek istiyoruz", "defense"),
    ("Kripto komuta ve telsiz altyapısı ihalelerine girmek istiyoruz", "defense"),
    ("Hava savunma sistemi yazılımı ve entegrasyonu arıyoruz", "defense"),
    ("Komuta kontrol sistemi yazılımı gerekiyor", "defense"),
    ("Siber güvenlik altyapısı ve saldırı tespit sistemi", "defense"),
    ("Birlikler arası kriptolu haberleşme entegrasyonu", "defense"),
    ("Savunma sanayi için yerli yazılım çözümü lazım", "defense"),
    ("İHA filo yönetim yazılımı hizmeti almak istiyoruz", "defense"),
    ("TSK lojistik yönetim sistemi entegrasyonu", "defense"),
    ("Kurumsal düzeyde insansız hava aracı kontrol yazılımı", "defense"),
    ("Elektronik harp sistemleri için yazılım geliştirme", "defense"),
    ("Askeri lojistik takip ve planlama yazılımı", "defense"),
    ("Denizaltı sonar veri işleme yazılımı", "defense"),
    ("Kara kuvvetleri personel yönetim sistemi yazılımı", "defense"),
    ("Savunma projesi için yerli yazılım geliştirme ortağı", "defense"),
    ("Mayın tespit ve imha sistemi yazılımı", "defense"),
    ("Gece görüş sistemi yazılım entegrasyonu", "defense"),
    ("Savaş simülatörü yazılımı geliştirme hizmeti", "defense"),

    # ── EGİTİM – 20 sorgu ──────────────────────────────────────────────────
    ("Öğrenci bilgi sistemi OBS entegrasyonuna ihtiyacımız var", "education"),
    ("Üniversite otomasyon sistemi hizmeti almak istiyoruz", "education"),
    ("LMS kurulumu için yazılım hizmeti gerekiyor", "education"),
    ("Kampüs içindeki tüm ağ ve donanım süreçlerini tek portaldan yönetmek", "education"),
    ("E-öğrenme platformu yazılımı geliştirmek istiyoruz", "education"),
    ("Sınav ve değerlendirme sistemi yazılımı arıyoruz", "education"),
    ("Üniversite kütüphanesi için dijital kataloglama otomasyonu", "education"),
    ("ÖBYS entegrasyonu yapacak yazılım firması arıyoruz", "education"),
    ("Öğrenci devam takip sistemi yazılımı", "education"),
    ("Akademik kadro yönetim sistemi entegrasyonu", "education"),
    ("Uzaktan eğitim altyapısı kurulumu ve yazılım desteği", "education"),
    ("Öğrenci burs yönetim sistemi yazılımı arıyoruz", "education"),
    ("Transkript ve diploma sistemleri entegrasyonu", "education"),
    ("Ders programı ve sınıf planlama yazılımı lazım", "education"),
    ("Öğrenci danışmanlık takip sistemi yazılımı", "education"),
    ("Kurumsal e-posta ve kampüs portal entegrasyonu", "education"),
    ("Öğrenci ödeme ve harç yönetim sistemi", "education"),
    ("Okul yönetim yazılımı kurulumu için teklif istiyoruz", "education"),
    ("Uzaktan eğitim platformu hizmeti almak istiyoruz", "education"),
    ("Çift anadal ve yandal başvuru yönetim yazılımı", "education"),

    # ── TURİZM – 20 sorgu ──────────────────────────────────────────────────
    ("Otel rezervasyon yazılımı hizmeti almak istiyoruz", "tourism"),
    ("Turizm acentası için paket tur satış platformu", "tourism"),
    ("Lüks otel zincirimiz için çevrimiçi biletleme motoru yazılımı", "tourism"),
    ("Konaklama yönetim sistemi entegrasyonu", "tourism"),
    ("Tatil paketi satış ve rezervasyon platformu", "tourism"),
    ("Otel check-in otomasyon yazılımı arıyoruz", "tourism"),
    ("Tur operatörü için CRM ve müşteri takip sistemi", "tourism"),
    ("PNR yönetim sistemi entegrasyonu lazım", "tourism"),
    ("Havayolu bilet satış yazılımı geliştirmek istiyoruz", "tourism"),
    ("Resort için misafir deneyimi yönetim yazılımı", "tourism"),
    ("Turizm işletmesi için online ödeme entegrasyonu", "tourism"),
    ("Otel fiyat yönetim ve kanal manager yazılımı", "tourism"),
    ("Seyahat acentası için B2B rezervasyon platformu", "tourism"),
    ("Müze için dijital biletleme ve ziyaretçi takip sistemi", "tourism"),
    ("Kamp ve outdoor turizm rezervasyon yazılımı", "tourism"),
    ("Termal otel için SPA yönetim yazılımı entegrasyonu", "tourism"),
    ("Kruvaziyer şirketi için yolcu yönetim sistemi", "tourism"),
    ("Personelimizin yıllık izinlerini planlayacak kurumsal tatil paketi", "tourism"),
    ("Golf sahası rezervasyon ve yönetim yazılımı", "tourism"),
    ("Uçak bileti ve otel kombine satış platformu", "tourism"),

    # ── OOD – 20 sorgu (REDDEDILMELI) ─────────────────────────────────────
    ("Havalar bugün nasıl?", "ood"),
    ("Savunma sanayi hisse senedi borsa fiyatları", "ood"),
    ("Kardiyoloji doktorundan randevu almak istiyorum", "ood"),  # B2C
    ("Üniversite güz dönemi harç ödememi nereye yapacağım?", "ood"),  # B2C
    ("Antalyada tatil yapmak istiyorum en ucuz otel", "ood"),  # B2C
    ("Bugün acil hastanenin önünde trafik kazası olmuş", "ood"),
    ("Eğitim uçakları için evime oyun bilgisayarı", "ood"),
    ("Kargo rotalarımızı optimize etmemiz lazım", "ood"),  # lojistik - dışarıda
    ("Bitcoin fiyatı ne kadar?", "ood"),
    ("Sosyal medya hesabım hacklendi ne yapmalıyım?", "ood"),
    ("Aselsan hisseleri bugün tavan yaptı mı?", "ood"),
    ("Pizza siparişi vermek istiyorum", "ood"),
    ("Araba tamiri için usta arıyorum", "ood"),
    ("İnsan kaynakları departmanı için bordro yazılımı", "ood"),  # İK - dışarıda
    ("E-ticaret sitesi kurmak istiyorum", "ood"),  # e-ticaret - dışarıda
    ("Sağlık/hastane değil, lojistik kargo rotası optimizasyonu", "ood"),
    ("Savunma sanayi şirketlerine yapılan kamu ihalelerinin sonuçları", "ood"),
    ("Sel felaketi haberlerini takip etmek istiyorum", "ood"),
    ("ERP sistemimizi güncellemek istiyoruz", "ood"),  # genel - dışarıda
    ("CRM yazılımı arıyoruz ama sektör belirtmiyoruz", "ood"),  # genel - dışarıda
]

assert len(TEST_DATA) == 100, f"Beklenen 100 sorgu, bulunan {len(TEST_DATA)}"

SECTOR_MAP = {
    "sağlık": "health", "saglik": "health",
    "turizm": "tourism",
    "savunma": "defense",
    "eğitim": "education", "egitim": "education",
}

def get_bge_score_and_sector(emb, query):
    hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
    if not hits:
        return 0.0, "ood"
    best = hits[0]
    score = float(best.score)
    meta_sector = (best.metadata or {}).get("beklened_sektor") or (best.metadata or {}).get("beklenen_sektor") or ""
    sector = SECTOR_MAP.get(str(meta_sector).strip().lower(), "ood")
    return score, sector


def main():
    print(f"Model yukleniyor...", flush=True)
    emb = get_embedder()

    print(f"{len(TEST_DATA)} sorgu isleniyor...", flush=True)
    results = []
    for i, (query, true_label) in enumerate(TEST_DATA):
        score, pred_sector = get_bge_score_and_sector(emb, query)
        results.append({
            "query": query,
            "true_label": true_label,
            "bge_score": score,
            "raw_pred": pred_sector,
        })
        if (i+1) % 20 == 0:
            print(f"  {i+1}/100 tamamlandi...", flush=True)

    print("\n" + "="*96)
    print(f"{'Esik':<8} | {'Dogruluk':>10} | {'Dogru Kabul(TA)':>16} | {'Yanlis Kabul(FAR)':>18} | {'Yanlis Red(FRR)':>16} | {'Toplam Dogru':>13}")
    print("="*96)

    thresholds = [i/100 for i in range(50, 87)]
    best_t, best_acc, best_stats = 0.0, 0.0, {}

    for t in thresholds:
        ta = fa = fr = tr_count = 0
        for r in results:
            final = r["raw_pred"] if r["bge_score"] >= t else "ood"
            actual = r["true_label"]
            is_ood = (actual == "ood")
            correct_reject = (final == "ood" and is_ood)
            correct_accept = (final == actual and not is_ood)
            if correct_reject: tr_count += 1
            elif correct_accept: ta += 1
            elif is_ood: fa += 1   # OOD ama içeri aldık
            else: fr += 1          # B2B ama reddettik (veya yanlış sektör)

        total_correct = ta + tr_count
        acc = total_correct / len(results)

        print(f"{t:.2f}     | {acc*100:>9.1f}% | {ta:>16} | {fa:>18} | {fr:>16} | {total_correct:>13}/100")

        if acc > best_acc and fa == 0:
            best_acc = acc
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}
        elif acc == best_acc and fa == 0 and t < best_t:
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}

    print("="*96)
    print(f"\n*** TAVSIYE EDILEN ESIK: {best_t:.2f} ***")
    print(f"    Dogruluk : %{best_acc*100:.1f}")
    print(f"    Dogru Kabul (TA)   : {best_stats.get('TA', 0)}/80  B2B sorular")
    print(f"    Yanlis Kabul (FAR) : {best_stats.get('FA', 0)}/20  OOD tuzak")
    print(f"    Yanlis Red (FRR)   : {best_stats.get('FR', 0)}/80  kaçırılan B2B")
    print(f"    Dogru Red  (TR)    : {best_stats.get('TR', 0)}/20  OOD dogru elendi")


if __name__ == "__main__":
    main()
