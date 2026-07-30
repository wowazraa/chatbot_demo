"""
1000 sorguluk kapsamli threshold tarama scripti.
Sorular programatik augmentation ile uretilir (prefix/suffix/typo/lang karistirma).
"""
import sys, os, logging, random
logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

sys.path.insert(0, ".")
from src.embedder import get_embedder

# ─────────────────────────────────────────────────────────────────────────────
# 1. SEED CUMLELER  (sektör başına 50 adet)
# ─────────────────────────────────────────────────────────────────────────────
SEEDS = {
    "health": [
        "hastane yönetim yazılımı", "klinik randevu otomasyonu", "poliklinik iş akışı yazılımı",
        "hasta takip sistemi", "HBYS entegrasyonu", "e-nabız entegrasyonu",
        "tele-tıp altyapısı", "ameliyathane yönetim yazılımı", "hekim takvim sistemi",
        "uzaktan sağlık asistanı", "AHBS entegrasyonu", "muayene yönetim sistemi",
        "radyoloji dijital görüntüleme yazılımı", "acil servis yönetim yazılımı",
        "laboratuvar takip sistemi", "hemşire iş akışı otomasyonu", "tıbbi cihaz bakım takibi",
        "kurumsal sağlık bilgi sistemi", "doktor performans takip yazılımı", "klinik veri analiz platformu",
        "poliklinik yazılımı", "hasta kayıt sistemi", "eczane yönetim yazılımı",
        "sağlık analitik platformu", "bölgesel sağlık ağı entegrasyonu",
        "diyaliz merkezi yönetim yazılımı", "patoloji laboratuvarı otomasyon sistemi",
        "hasta faturalandırma yazılımı", "sağlık sigortası entegrasyon yazılımı",
        "mobil sağlık uygulaması geliştirme", "gece nöbeti planlama yazılımı",
        "sterilizasyon takip sistemi", "biyomedikal cihaz yönetimi",
        "tıbbi kayıt dijitalleştirme hizmeti", "röntgen arşiv sistemi PACS",
        "sağlık portalı yazılımı", "klinik test yönetim sistemi",
        "yoğun bakım takip yazılımı", "psikiyatri klinik yazılımı",
        "diş kliniği yönetim sistemi", "optisyen yönetim yazılımı",
        "fizyoterapi klinik yazılımı", "onkoloji vaka takip sistemi",
        "hematoloji laboratuvar yazılımı", "nöroloji klinik veri sistemi",
        "kardiyoloji takip yazılımı kurumsal", "ortopedi klinik yönetimi",
        "tıbbi görüntü işleme yazılımı", "klinik karar destek sistemi",
        "sağlık hizmetleri kalite güvence yazılımı",
    ],
    "defense": [
        "radar veri analiz yazılımı", "insansız hava aracı kontrol yazılımı",
        "askeri haberleşme altyapısı", "kripto komuta telsiz altyapısı",
        "hava savunma sistemi yazılımı", "komuta kontrol sistemi",
        "siber güvenlik saldırı tespit sistemi", "kriptolu haberleşme entegrasyonu",
        "savunma sanayi yerli yazılım", "İHA filo yönetim yazılımı",
        "TSK lojistik yönetim sistemi", "elektronik harp yazılımı",
        "askeri lojistik takip yazılımı", "denizaltı sonar yazılımı",
        "kara kuvvetleri personel yönetim sistemi", "savunma projesi yazılım geliştirme",
        "mayın tespit sistemi yazılımı", "gece görüş sistemi entegrasyonu",
        "savaş simülatörü yazılımı", "zırhlı araç kontrol yazılımı",
        "füze güdüm sistemi yazılımı", "savunma bütçe planlama sistemi",
        "askeri envanter yönetim yazılımı", "NATO uyumlu haberleşme sistemi",
        "saha komuta kontrol uygulaması", "radar izleme ve takip yazılımı",
        "hava trafik kontrol yazılımı savunma", "silahlı İHA yazılım entegrasyonu",
        "uydu haberleşme şifreleme yazılımı", "deniz gücü operasyon yazılımı",
        "elektronik istihbarat yazılımı", "hedef tespit ve tanıma yazılımı",
        "kriptografik protokol entegrasyonu", "askeri proje yönetim yazılımı",
        "güvenli veri aktarım sistemi savunma", "savunma tedarik zinciri yazılımı",
        "muharebe simülasyon platformu", "hava ikmal sistemi yazılımı",
        "çok fonksiyonlu radar yazılımı", "savunma Ar-Ge yönetim platformu",
        "deniz mayını tespit yazılımı", "topçu ateş kontrol sistemi",
        "gözetleme kamera analitik yazılımı savunma", "askeri harita ve coğrafi bilgi sistemi",
        "savunma sanayi ihale takip yazılımı", "kara radar entegrasyonu",
        "insansız deniz aracı kontrol yazılımı", "siber savunma operasyon merkezi yazılımı",
        "savunma sanayi ERP sistemi", "ASELSAN entegrasyon yazılımı",
    ],
    "education": [
        "öğrenci bilgi sistemi OBS", "üniversite otomasyon sistemi",
        "LMS kurulumu yazılımı", "kampüs yönetim sistemi",
        "e-öğrenme platformu", "sınav değerlendirme sistemi",
        "üniversite kütüphane otomasyon sistemi", "ÖBYS entegrasyonu",
        "öğrenci devam takip sistemi", "akademik kadro yönetim sistemi",
        "uzaktan eğitim altyapısı", "öğrenci burs yönetim sistemi",
        "transkript diploma sistemi", "ders programı planlama yazılımı",
        "öğrenci danışmanlık sistemi", "kampüs portal entegrasyonu",
        "öğrenci harç yönetim sistemi", "okul yönetim yazılımı",
        "çift anadal yönetim yazılımı", "yaz okulu kayıt sistemi",
        "öğrenci kariyer merkezi yazılımı", "mezuniyet takip sistemi",
        "öğrenci etkinlik yönetim platformu", "dijital sınıf yönetim yazılımı",
        "eğitim analitik platformu", "öğrenci geri bildirim sistemi",
        "akademik değerlendirme yazılımı", "öğrenci kimlik kart sistemi",
        "kampüs güvenlik yönetim yazılımı", "öğrenci yurt yönetim sistemi",
        "eğitim ERP sistemi", "öğrenci sağlık merkezi yazılımı",
        "ilköğretim okul yönetim yazılımı", "lise otomasyon sistemi",
        "mesleki eğitim kurumu yazılımı", "sertifika ve belge yönetim sistemi",
        "öğrenci proje takip yazılımı", "akademik takvim planlama sistemi",
        "e-sınav güvenlik yazılımı", "eğitim kurumu muhasebe yazılımı",
        "staj takip yönetim sistemi", "mezun takip sistemi",
        "öğretmen performans değerlendirme sistemi", "öğrenci mentoring platformu",
        "kampüs Wi-Fi yönetim yazılımı", "öğrenci giriş çıkış takip sistemi",
        "interaktif akıllı tahta yazılımı", "dijital öğrenci portföy sistemi",
        "çevrimiçi sınav platformu", "öğrenci beklenti analiz yazılımı",
    ],
    "tourism": [
        "otel rezervasyon yazılımı", "turizm acentası tur satış platformu",
        "otel biletleme motoru yazılımı", "konaklama yönetim sistemi",
        "tatil paketi satış platformu", "otel check-in otomasyon yazılımı",
        "tur operatörü CRM sistemi", "PNR yönetim sistemi",
        "havayolu bilet satış yazılımı", "resort misafir deneyim yazılımı",
        "online ödeme entegrasyonu turizm", "otel fiyat kanal manager yazılımı",
        "seyahat acentası B2B rezervasyon", "müze dijital biletleme sistemi",
        "kamp outdoor rezervasyon yazılımı", "termal otel SPA yönetim yazılımı",
        "kruvaziyer yolcu yönetim sistemi", "kurumsal tatil planlama yazılımı",
        "golf sahası rezervasyon yazılımı", "uçak otel kombine satış platformu",
        "butik otel yönetim yazılımı", "kış turizmi kayak merkezi yazılımı",
        "tur rehberi takip sistemi", "turizm analitik platformu",
        "otel gelir yönetim yazılımı", "misafir sadakat programı yazılımı",
        "villa kiralama yönetim platformu", "etkinlik organizasyon yazılımı turizm",
        "yat marina yönetim sistemi", "kültür turu dijital rehberlik yazılımı",
        "otel temizlik yönetim yazılımı", "oda servisi otomasyon sistemi",
        "kongre toplantı yönetim yazılımı", "seyahat sigortası entegrasyon yazılımı",
        "transfer ve ulaşım yönetim yazılımı", "vize takip entegrasyon sistemi",
        "turizm ihracat platformu yazılımı", "otel insan kaynakları yazılımı",
        "sağlık turizmi yönetim yazılımı", "agro turizm rezervasyon platformu",
        "turizm bakanlığı entegrasyon yazılımı", "otel enerji yönetim sistemi",
        "misafir deneyim anketi platformu", "turizm şikayeti takip sistemi",
        "otel havuz fitness yönetim yazılımı", "restoran rezervasyon entegrasyon sistemi",
        "turizm franchise yönetim yazılımı", "çevrimiçi seyahat acentası platformu",
        "otel güvenlik yönetim yazılımı", "turizm raporlama analitik yazılımı",
    ],
    "ood": [
        "havalar bugün nasıl", "borsa fiyatları ne kadar",
        "kardiyoloji doktorundan randevu almak istiyorum",  # B2C
        "üniversite harç ödememi nereye yapacağım",        # B2C
        "antalyada en ucuz otel bulmak istiyorum",         # B2C
        "trafik kazası haberleri", "oyun bilgisayarı fiyatları",
        "kargo rota optimizasyonu",  # lojistik dışında
        "bitcoin fiyatı", "sosyal medya hesap güvenliği",
        "aselsan hisse senedi", "pizza sipariş vermek",
        "araba tamiri usta", "bordro yazılımı",            # İK sektörü
        "e-ticaret sitesi kurmak istiyorum",               # e-ticaret
        "muhasebe yazılımı ERP genel",                     # genel ERP
        "CRM yazılımı arıyoruz sektörsüz",                 # genel CRM
        "sel felaketi haber takibi", "kripto para yatırımı",
        "tarım sulama sistemi yazılımı",                   # tarım sektörü
        "inşaat proje yönetim yazılımı",                   # inşaat
        "otomobil satış platformu yazılımı",               # otomotive
        "perakende mağaza yönetim yazılımı",               # perakende
        "finans sektörü risk analiz yazılımı",             # finans
        "elektrik dağıtım şebeke yönetim yazılımı",       # enerji
        "iklim değişikliği raporu haberleri",
        "uluslararası nakliye lojistik sistemi",
        "hukuk bürosu dava takip yazılımı",                # hukuk
        "spor kulübü yönetim yazılımı",                    # spor
        "medya yayın akış platformu yazılımı",             # medya
        "emlak gayrimenkul yönetim yazılımı",              # gayrimenkul
        "restoran yönetim yazılımı",                       # F&B
        "sağlık eğitim hastane değil yazılım değil genel bilgi",
        "yapay zeka genel danışmanlık hizmeti",
        "blockchain tabanlı tedarik zinciri genel",
        "veri merkezi altyapı yönetimi genel",
        "nesnelerin interneti IoT platformu genel",
        "bulut bilişim geçiş danışmanlığı genel",
        "sigorta hasar yönetim yazılımı",                  # sigorta
        "enerji verimliliği izleme yazılımı",              # enerji
        "kamu yönetim e-devlet yazılımı genel",            # e-devlet genel
        "çevre izleme sistemi yazılımı",                   # çevre
        "tarım drone ilaçlama yazılımı",                   # tarım
        "güzellik salonu yönetim yazılımı",                # güzellik
        "veteriner klinik yazılımı",                       # veteriner
        "optik mağaza yönetim yazılımı bireysel",          # bireysel optik
        "fırın pastane yönetim yazılımı",                  # F&B
        "çocuk kreş yönetim yazılımı",                     # eğitim ama erken çocukluk farklı
        "berber kuaför yönetim yazılımı",                  # güzellik
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. AUGMENTATION PARAMETRELERI
# ─────────────────────────────────────────────────────────────────────────────
PREFIXES = [
    "lütfen", "acil olarak", "şirketimiz için", "kurumsal düzeyde",
    "bize", "hızlıca", "yeni bir", "acaba", "şirketimiz olarak",
    "kurum olarak", "projemiz için", "ihale kapsamında",
    "çözüm ortağı arıyoruz:", "merhaba",
]
SUFFIXES = [
    "entegrasyonu istiyoruz", "yazılımı gerekiyor", "çözümüne ihtiyacımız var",
    "sistemi lazım", "altyapısı kurulacak", "hizmeti almak istiyoruz",
    "konusunda teklif istiyoruz", "için firma arıyoruz",
    "modülü lazım", "platformu kurmak istiyoruz",
]
TYPOS = {
    "yazılımı": ["yazilimi", "yazlımı", "yazılmi"],
    "sistemi": ["sistemi", "sistmi"],
    "entegrasyonu": ["entegrasyonu", "entegrasyon"],
    "hizmeti": ["hizmti", "hizmeti"],
    "kurulumu": ["kurulumu", "kurulmu"],
}

random.seed(42)


def augment(seed: str, label: str, n: int) -> list[tuple[str, str]]:
    out = []
    words = seed.split()
    for _ in range(n):
        s = seed
        # Rastgele prefix ekle
        if random.random() < 0.4:
            s = random.choice(PREFIXES) + " " + s
        # Rastgele suffix ekle (OOD sorgularda daha az)
        if label != "ood" and random.random() < 0.5:
            s = s + " " + random.choice(SUFFIXES)
        # Küçük yazım varyasyonu
        for orig, variants in TYPOS.items():
            if orig in s and random.random() < 0.2:
                s = s.replace(orig, random.choice(variants), 1)
        out.append((s.strip(), label))
    return out


def build_dataset(target: int = 1000) -> list[tuple[str, str]]:
    per_sector = target // len(SEEDS)   # 200 her sektör
    data = []
    for label, seeds in SEEDS.items():
        base = [(s, label) for s in seeds]
        data.extend(base)
        remaining = per_sector - len(base)
        for i in range(remaining):
            seed = seeds[i % len(seeds)]
            data.extend(augment(seed, label, 1))
    # Karıştır
    random.shuffle(data)
    return data[:target]


# ─────────────────────────────────────────────────────────────────────────────
# 3. ANA AKIŞ
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_MAP = {
    "sağlık": "health", "saglik": "health",
    "turizm": "tourism", "savunma": "defense",
    "eğitim": "education", "egitim": "education",
}


def main():
    dataset = build_dataset(1000)
    label_counts = {}
    for _, lbl in dataset:
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
    print(f"Dataset: {len(dataset)} sorgu | Dagılım: {label_counts}", flush=True)

    print("Model yukleniyor...", flush=True)
    emb = get_embedder()

    print(f"Sorgular isleniyor...", flush=True)
    results = []
    for i, (query, true_label) in enumerate(dataset):
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            score, pred = 0.0, "ood"
        else:
            best = hits[0]
            score = float(best.score)
            meta = (best.metadata or {}).get("beklenen_sektor") or ""
            pred = SECTOR_MAP.get(str(meta).strip().lower(), "ood")
        results.append({"true": true_label, "pred": pred, "score": score})
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/1000 tamamlandi...", flush=True)

    # OOD sayısı
    n_ood = sum(1 for r in results if r["true"] == "ood")
    n_b2b = len(results) - n_ood

    print("\n" + "=" * 106)
    print(f"{'Esik':<7} | {'Dogruluk':>9} | {'TA(B2B OK)':>12} | {'FAR(OOD->B2B)':>15} | {'FRR(B2B->OOD)':>15} | {'TR(OOD OK)':>12} | {'Dogru/1000':>10}")
    print("=" * 106)

    thresholds = [i / 100 for i in range(50, 87)]
    best_t, best_acc, best_stats = 0.0, 0.0, {}

    for t in thresholds:
        ta = fa = fr = tr_count = 0
        for r in results:
            final = r["pred"] if r["score"] >= t else "ood"
            is_ood = (r["true"] == "ood")
            if is_ood and final == "ood":
                tr_count += 1
            elif not is_ood and final == r["true"]:
                ta += 1
            elif is_ood and final != "ood":
                fa += 1
            else:
                fr += 1

        total_correct = ta + tr_count
        acc = total_correct / len(results)
        far_pct = fa / n_ood * 100 if n_ood else 0

        flag = " <-- UYARI FAR>0" if fa > 0 else ""
        print(f"{t:.2f}    | {acc*100:>8.1f}% | {ta:>10}/{n_b2b} | {fa:>8} (%{far_pct:.0f}){'':<5} | {fr:>10}/{n_b2b} | {tr_count:>8}/{n_ood} | {total_correct:>6}/1000{flag}")

        if acc > best_acc and fa == 0:
            best_acc, best_t = acc, t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}
        elif acc == best_acc and fa == 0 and t < best_t:
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}

    print("=" * 106)
    print(f"\n*** EN IYI ESIK (FAR=0 sartiyla): {best_t:.2f} ***")
    print(f"    Genel Dogruluk : %{best_acc * 100:.1f}")
    print(f"    Dogru Kabul TA : {best_stats.get('TA', 0)}/{n_b2b}")
    print(f"    Yanlis Red FRR : {best_stats.get('FR', 0)}/{n_b2b}")
    print(f"    Yanlis Kabul FA: {best_stats.get('FA', 0)}/{n_ood}  (SIFIR olmali!)")
    print(f"    Dogru Red TR   : {best_stats.get('TR', 0)}/{n_ood}")


if __name__ == "__main__":
    main()
