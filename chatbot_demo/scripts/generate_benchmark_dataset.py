"""
Senior QA & Benchmark Engineer - B2B Sector Intent Router Stress Test Dataset Generator
Generates 1000-line benchmark dataset with realistic noise and adversarial examples.
"""
import json
import random
from typing import List, Dict

random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# 1. IN-DOMAIN SEED QUERIES (Clean B2B)
# ─────────────────────────────────────────────────────────────────────────────
IN_DOMAIN_SEEDS = {
    "health": [
        "klinik hasta takip yazılımı fiyatları",
        "hastane yönetim sistemi entegrasyonu",
        "HBYS kurulum ve danışmanlık hizmeti",
        "poliklinik randevu otomasyon sistemi",
        "e-nabız entegrasyonlu sağlık yazılımı",
        "radyoloji dijital görüntüleme sistemi PACS",
        "laboratuvar bilgi sistemi LIS kurulumu",
        "eczane yönetim otomasyon yazılımı",
        "yoğun bakım hasta takip sistemi",
        "ameliyathane yönetim yazılımı",
        "doktor performans takip sistemi",
        "klinik karar destek sistemi",
        "sağlık sigortası entegrasyon yazılımı",
        "tele-tıp altyapısı kurulumu",
        "mobil sağlık uygulaması geliştirme",
        "tıbbi cihaz bakım takip sistemi",
        "sterilizasyon takip yazılımı",
        "biyomedikal cihaz yönetimi",
        "kurumsal sağlık bilgi sistemi",
        "bölgesel sağlık ağı entegrasyonu",
        "diyaliz merkezi yönetim yazılımı",
        "patoloji laboratuvarı otomasyonu",
        "hasta faturalandırma sistemi",
        "sağlık analitik platformu",
        "klinik veri analiz sistemi",
        "hasta kayıt dijitalleştirme",
        "röntgen arşiv yönetim sistemi",
        "sağlık portalı yazılımı",
        "klinik test yönetim sistemi",
        "psikiyatri klinik otomasyonu",
        "diş kliniği yönetim sistemi",
        "optisyen yönetim yazılımı",
        "fizyoterapi klinik yazılımı",
        "onkoloji vaka takip sistemi",
        "hematoloji laboratuvar yazılımı",
        "nöroloji klinik veri sistemi",
        "kardiyoloji takip yazılımı",
        "ortopedi klinik yönetimi",
        "tıbbi görüntü işleme yazılımı",
        "sağlık hizmetleri kalite güvence",
        "gece nöbeti planlama sistemi",
        "hekim takvim yönetim yazılımı",
        "uzaktan sağlık asistanı",
        "AHBS entegrasyonu",
        "muayene yönetim sistemi",
        "hemşire iş akışı otomasyonu",
        "tıbbi kayıt dijitalleştirme",
    ],
    "defense": [
        "radar veri analiz yazılımı",
        "insansız hava aracı kontrol yazılımı",
        "askeri haberleşme altyapısı",
        "kripto komuta telsiz sistemi",
        "hava savunma sistemi yazılımı",
        "komuta kontrol sistemi C2",
        "siber güvenlik saldırı tespit sistemi",
        "kriptolu haberleşme entegrasyonu",
        "savunma sanayi yerli yazılım",
        "İHA filo yönetim yazılımı",
        "TSK lojistik yönetim sistemi",
        "elektronik harp yazılımı",
        "askeri lojistik takip sistemi",
        "denizaltı sonar yazılımı",
        "kara kuvvetleri personel sistemi",
        "savunma projesi yazılım geliştirme",
        "mayın tespit sistemi yazılımı",
        "gece görüş sistemi entegrasyonu",
        "savaş simülatörü yazılımı",
        "zırhlı araç kontrol yazılımı",
        "füze güdüm sistemi yazılımı",
        "savunma bütçe planlama sistemi",
        "askeri envanter yönetim yazılımı",
        "NATO uyumlu haberleşme sistemi",
        "saha komuta kontrol uygulaması",
        "radar izleme ve takip yazılımı",
        "hava trafik kontrol yazılımı",
        "silahlı İHA yazılım entegrasyonu",
        "uydu haberleşme şifreleme yazılımı",
        "deniz gücü operasyon yazılımı",
        "elektronik istihbarat yazılımı",
        "hedef tespit ve tanıma yazılımı",
        "kriptografik protokol entegrasyonu",
        "askeri proje yönetim yazılımı",
        "güvenli veri aktarım sistemi",
        "savunma tedarik zinciri yazılımı",
        "muharebe simülasyon platformu",
        "hava ikmal sistemi yazılımı",
        "çok fonksiyonlu radar yazılımı",
        "savunma Ar-Ge yönetim platformu",
        "deniz mayını tespit yazılımı",
        "topçu ateş kontrol sistemi",
        "gözetleme kamera analitik yazılımı",
        "askeri harita ve coğrafi bilgi sistemi",
        "savunma sanayi ihale takip yazılımı",
        "kara radar entegrasyonu",
        "insansız deniz aracı kontrol yazılımı",
        "siber savunma operasyon merkezi yazılımı",
        "savunma sanayi ERP sistemi",
        "ASELSAN entegrasyon yazılımı",
    ],
    "education": [
        "öğrenci bilgi sistemi OBS",
        "üniversite otomasyon sistemi",
        "LMS kurulum yazılımı",
        "kampüs yönetim sistemi",
        "e-öğrenme platformu",
        "sınav değerlendirme sistemi",
        "üniversite kütüphane otomasyonu",
        "ÖBYS entegrasyonu",
        "öğrenci devam takip sistemi",
        "akademik kadro yönetim sistemi",
        "uzaktan eğitim altyapısı",
        "öğrenci burs yönetim sistemi",
        "transkript diploma sistemi",
        "ders programı planlama yazılımı",
        "öğrenci danışmanlık sistemi",
        "kampüs portal entegrasyonu",
        "öğrenci harç yönetim sistemi",
        "okul yönetim yazılımı",
        "çift anadal yönetim yazılımı",
        "yaz okulu kayıt sistemi",
        "öğrenci kariyer merkezi yazılımı",
        "mezuniyet takip sistemi",
        "öğrenci etkinlik yönetim platformu",
        "dijital sınıf yönetim yazılımı",
        "eğitim analitik platformu",
        "öğrenci geri bildirim sistemi",
        "akademik değerlendirme yazılımı",
        "öğrenci kimlik kart sistemi",
        "kampüs güvenlik yönetim yazılımı",
        "öğrenci yurt yönetim sistemi",
        "eğitim ERP sistemi",
        "öğrenci sağlık merkezi yazılımı",
        "ilköğretim okul yönetim yazılımı",
        "lise otomasyon sistemi",
        "mesleki eğitim kurumu yazılımı",
        "sertifika ve belge yönetim sistemi",
        "öğrenci proje takip yazılımı",
        "akademik takvim planlama sistemi",
        "e-sınav güvenlik yazılımı",
        "eğitim kurumu muhasebe yazılımı",
        "staj takip yönetim sistemi",
        "mezun takip sistemi",
        "öğretmen performans değerlendirme sistemi",
        "öğrenci mentoring platformu",
        "kampüs Wi-Fi yönetim yazılımı",
        "öğrenci giriş çıkış takip sistemi",
        "interaktif akıllı tahta yazılımı",
        "dijital öğrenci portföy sistemi",
        "çevrimiçi sınav platformu",
        "öğrenci beklenti analiz yazılımı",
    ],
    "tourism": [
        "otel rezervasyon yazılımı",
        "turizm acentası tur satış platformu",
        "otel biletleme motoru yazılımı",
        "konaklama yönetim sistemi PMS",
        "tatil paketi satış platformu",
        "otel check-in otomasyon yazılımı",
        "tur operatörü CRM sistemi",
        "PNR yönetim sistemi",
        "havayolu bilet satış yazılımı",
        "resort misafir deneyim yazılımı",
        "online ödeme entegrasyonu turizm",
        "otel fiyat kanal manager yazılımı",
        "seyahat acentası B2B rezervasyon",
        "müze dijital biletleme sistemi",
        "kamp outdoor rezervasyon yazılımı",
        "termal otel SPA yönetim yazılımı",
        "kruvaziyer yolcu yönetim sistemi",
        "kurumsal tatil planlama yazılımı",
        "golf sahası rezervasyon yazılımı",
        "uçak otel kombine satış platformu",
        "butik otel yönetim yazılımı",
        "kış turizmi kayak merkezi yazılımı",
        "tur rehberi takip sistemi",
        "turizm analitik platformu",
        "otel gelir yönetim yazılımı",
        "misafir sadakat programı yazılımı",
        "villa kiralama yönetim platformu",
        "etkinlik organizasyon yazılımı turizm",
        "yat marina yönetim sistemi",
        "kültür turu dijital rehberlik yazılımı",
        "otel temizlik yönetim yazılımı",
        "oda servisi otomasyon sistemi",
        "kongre toplantı yönetim yazılımı",
        "seyahat sigortası entegrasyon yazılımı",
        "transfer ve ulaşım yönetim yazılımı",
        "vize takip entegrasyon sistemi",
        "turizm ihracat platformu yazılımı",
        "otel insan kaynakları yazılımı",
        "sağlık turizmi yönetim yazılımı",
        "agro turizm rezervasyon platformu",
        "turizm bakanlığı entegrasyon yazılımı",
        "otel enerji yönetim sistemi",
        "misafir deneyim anketi platformu",
        "turizm şikayeti takip sistemi",
        "otel havuz fitness yönetim yazılımı",
        "restoran rezervasyon entegrasyon sistemi",
        "turizm franchise yönetim yazılımı",
        "çevrimiçi seyahat acentası platformu",
        "otel güvenlik yönetim yazılımı",
        "turizm raporlama analitik yazılımı",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. NOISE GENERATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
TYPO_PATTERNS = {
    "yazılımı": ["yazilimi", "yazlımı", "yazılmi", "yazılmı"],
    "sistemi": ["sistemi", "sistmi", "sistemi"],
    "entegrasyonu": ["entegrasyonu", "entegrasyon", "entegrasyon"],
    "yönetim": ["yonetim", "yönetım", "yonetım"],
    "kurulumu": ["kurulumu", "kurulmu", "kurulmu"],
    "otomasyon": ["otomasyon", "otomasyon", "otomasyon"],
    "hastane": ["hastne", "hastane", "hastane"],
    "otel": ["otl", "otel", "otel"],
    "rezervasyon": ["rezervsyon", "rezervasyon", "rezervasyon"],
    "klinik": ["klnik", "klinik", "klinik"],
}

ABBREVIATIONS = {
    "hasta bilgi yönetim sistemi": "HBYS",
    "öğrenci bilgi sistemi": "OBS",
    "öğrenci bilgi yönetim sistemi": "ÖBYS",
    "öğrenme yönetim sistemi": "LMS",
    "property management system": "PMS",
    "property management": "PMS",
    "konaklama yönetim sistemi": "PMS",
    "insansız hava aracı": "İHA",
    "elektronik sağlık kaydı": "ESK",
    "e-nabız": "e-nabız",
    "ameliyathane bilgi sistemi": "AİS",
    "laboratuvar bilgi sistemi": "LIS",
    "radyoloji bilgi sistemi": "RIS",
    "picture archiving": "PACS",
    "komuta kontrol": "C2",
}

SHORT_SEARCH_TERMS = {
    "health": ["hbys fiyat", "klinik yazılım", "hastane sistem", "sağlık otomasyon", "takip sistemi"],
    "defense": ["radar yazılım", "İHA kontrol", "savunma sistem", "askeri yazılım", "komuta kontrol"],
    "education": ["obs sistem", "lms kurulum", "okul yazılım", "öğrenci sistemi", "üniversite otomasyon"],
    "tourism": ["otel yazılım", "pms sistem", "rezervasyon", "turizm yazılım", "acente sistemi"],
}

def add_typo_noise(query: str) -> str:
    """Add realistic typo noise to query."""
    words = query.split()
    for i, word in enumerate(words):
        for original, variants in TYPO_PATTERNS.items():
            if original.lower() in word.lower() and random.random() < 0.3:
                words[i] = word.replace(original, random.choice(variants), 1)
                break
    return " ".join(words)

def add_abbreviation_noise(query: str) -> str:
    """Add abbreviation/jargon noise to query."""
    for full, abbrev in ABBREVIATIONS.items():
        if full.lower() in query.lower() and random.random() < 0.4:
            query = query.replace(full, abbrev, 1)
    return query

def create_short_search(sector: str) -> str:
    """Create short search-style query."""
    return random.choice(SHORT_SEARCH_TERMS[sector])

# ─────────────────────────────────────────────────────────────────────────────
# 3. ADVERSARIAL OOD SEED QUERIES (B2B format, non-target sectors)
# ─────────────────────────────────────────────────────────────────────────────
ADVERSARIAL_OOD_SEEDS = [
    # İnsan Kaynakları / Muhasebe
    "Personel maaş bordrosu ve özlük işleri otomasyonu",
    "İK performans değerlendirme sistemi",
    "Çalışan giriş çıkış takip sistemi",
    "Maaş hesaplama ve SGK bildirge yazılımı",
    "İnsan kaynakları modülü entegrasyonu",
    "Personel izin ve tatil yönetim sistemi",
    "Kurumsal iç iletişim platformu",
    "Çalışan eğitim ve gelişim takip sistemi",
    "Özlük dosyası dijitalleştirme hizmeti",
    "İK analitik ve raporlama sistemi",
    "Muhasebe defteri kefi ve fatura yazılımı",
    "E-fatura ve e-defter entegrasyonu",
    "Cari hesap takip ve muhasebe sistemi",
    "Genel muhasebe ve maliyet hesaplama yazılımı",
    "Beyanname ve vergi otomasyon sistemi",
    "Banka entegrasyonlu ödeme sistemi",
    "Nakit akış yönetim yazılımı",
    "Bütçe planlama ve kontrol sistemi",
    "Finansal raporlama platformu",
    "Hazine ve risk yönetim yazılımı",
    
    # E-Ticaret / Lojistik
    "E-ticaret sepet ve ödeme altyapısı entegrasyonu",
    "Online satış platformu kurulumu",
    "Mobil uygulama e-ticaret altyapısı",
    "Ürün katalog ve stok yönetim sistemi",
    "Müşteri ilişkileri yönetimi CRM e-ticaret",
    "Pazar yerleri entegrasyon yazılımı",
    "Kargo ve kurye takip sistemi",
    "Depo stok ve lojistik yönetim yazılımı",
    "Fulfillment merkezi otomasyonu",
    "Son kilometre teslimat optimizasyonu",
    "Tedarik zinciri yönetim sistemi",
    "Satın alma ve tedarik otomasyonu",
    "Lojistik rota optimizasyon yazılımı",
    "Filo yönetim ve araç takip sistemi",
    "Soğuk zincir lojistik izleme",
    
    # İnşaat / Gayrimenkul
    "Şantiye hakediş ve malzeme takip yazılımı",
    "İnşaat proje yönetim sistemi",
    "Bina yönetim yazılımı",
    "Gayrimenkul satış ve kiralık platformu",
    "Emlak portföy yönetim sistemi",
    "Müşteri takip ve satış otomasyonu",
    "Tapu ve kadastro entegrasyonu",
    "Kira kontrat yönetim sistemi",
    "Site yönetim ve aidat takip",
    "İnşaat malzeme stok sistemi",
    "Müteahhitlik hesap ve hakediş yazılımı",
    "Bina enerji yönetim sistemi",
    "Akıllı bina otomasyonu",
    "Yapı denetim ve kalite sistemi",
    "İş güvenliği takip yazılımı",
    
    # Hukuk
    "Dava ve icra takip otomasyonu",
    "Hukuk bürosu yönetim yazılımı",
    "Avukatlık dosya takip sistemi",
    "Duruşma ve takvim yönetimi",
    "Hukuki araştırma ve belge sistemi",
    "Sözleşme yönetim ve arşiv yazılımı",
    "Müvekkil ilişkileri yönetimi",
    "Hukuk bürosu muhasebe sistemi",
    "Dijital imza ve e-imza entegrasyonu",
    "Yasal uyum ve raporlama sistemi",
    "Arbitraj ve danışmanlık yazılımı",
    "Fikri mülkiyet takip sistemi",
    "Şirket kuruluş ve değişiklik takibi",
    "Vergi danışmanlığı otomasyonu",
    "İcra ve iflas takip sistemi",
    
    # Madencilik / Enerji
    "Maden sahası üretim takip sistemi",
    "Kömür ve maden operasyon yazılımı",
    "Enerji üretim ve dağıtım sistemi",
    "Elektrik şebeke yönetim yazılımı",
    "Yenilenebilir enerji izleme platformu",
    "Güneş enerjisi santral yönetimi",
    "Rüzgar enerjisi takip sistemi",
    "Petrol ve gaz arama yazılımı",
    "Boru hattı ve taşıma sistemi",
    "Enerji ticaret ve borsa entegrasyonu",
    "Su ve atık su yönetim sistemi",
    "Çevresel etki değerlendirme yazılımı",
    "Atık yönetim ve geri dönüşüm sistemi",
    "Endüstriyel emisyon takip",
    "Maden güvenliği ve denetim sistemi",
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. B2C / GENERAL NOISE QUERIES
# ─────────────────────────────────────────────────────────────────────────────
B2C_NOISE_SEEDS = [
    # B2C sağlık bilgileri
    "doktor çalışma saatleri",
    "hastane randevu nasıl alınır",
    "en iyi doktor tavsiyesi",
    "diş hekimi fiyatları",
    "göz muayenesi nerede yapılır",
    "acil servis telefon numarası",
    "eczane nöbetçi bul",
    "sağlık sigortası karşılaştırma",
    "özel hastane yorumları",
    "tahlil sonucu öğrenme",
    
    # B2C turizm bilgileri
    "uçak bileti fiyatları",
    "en iyi oteller yorumları",
    "tatil yerleri önerileri",
    "otel rezervasyon iptal",
    "gece treni biletleri",
    "yurtdışı seyahat vize",
    "turistik yerler haritası",
    "butik otel tavsiyeleri",
    "all inclusive otel fiyatları",
    "kamp alanı önerileri",
    
    # B2C eğitim bilgileri
    "üniversite taban puanları",
    "LYS puan hesaplama",
    "yurt başvuru şartları",
    "burs imkanları",
    "özel ders fiyatları",
    "online kurs tavsiyeleri",
    "yabancı dil kursu",
    "meslek lisesi kontenjanları",
    "yüksek lisans başvuru",
    "mezuniyet belgesi nasıl alınır",
    
    # Genel bilgi arama
    "hava durumu 7 günlük",
    "döviz kurları canlı",
    "borsa endeksleri",
    "altın fiyatları gram",
    "benzin litre fiyatı",
    "elektrik kesintisi sorgulama",
    "su faturası ödeme",
    " Vergi borcu sorgulama",
    "kimlik kartı başvuru",
    "pasaport randevu alma",
    
    # B2C alışveriş
    "en ucuz telefon fiyatları",
    "laptop önerileri 2024",
    "beyaz eşya indirimleri",
    "online alışveriş siteleri",
    "kargo takip numarası",
    "iade ve değişim politikası",
    "mobil telefon operatörleri",
    "internet paketi karşılaştırma",
    "kredi kartı başvuru",
    "banka kredi faiz oranları",
    
    # Eğlence ve yaşam
    "sinema seansları",
    "konser biletleri satış",
    "tiyatro oyunları programı",
    "restoran menü fiyatları",
    "cafe önerileri",
    "spor salonu üyelik",
    "fitness center fiyatları",
    "yüzme kursu kayıt",
    "yoga dersi programı",
    "pilot eğitimi nasıl alınır",
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. DATASET GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_in_domain_queries() -> List[Dict]:
    """Generate 700 In-Domain B2B queries with noise variations."""
    queries = []
    query_id = 1
    
    for sector, seeds in IN_DOMAIN_SEEDS.items():
        # Distribution: 60% clean (105), 15% typo (26), 15% abbrev (26), 10% short (18)
        clean_count = 105
        typo_count = 26
        abbrev_count = 26
        short_count = 18
        
        # Clean B2B queries
        for i in range(clean_count):
            seed = seeds[i % len(seeds)]
            queries.append({
                "id": query_id,
                "query": seed,
                "is_in_domain": True,
                "actual_sector": sector,
                "query_type": "clean_b2b"
            })
            query_id += 1
        
        # Typo queries
        for i in range(typo_count):
            seed = seeds[(clean_count + i) % len(seeds)]
            noisy_query = add_typo_noise(seed)
            queries.append({
                "id": query_id,
                "query": noisy_query,
                "is_in_domain": True,
                "actual_sector": sector,
                "query_type": "noisy_typo"
            })
            query_id += 1
        
        # Abbreviation queries
        for i in range(abbrev_count):
            seed = seeds[(clean_count + typo_count + i) % len(seeds)]
            noisy_query = add_abbreviation_noise(seed)
            queries.append({
                "id": query_id,
                "query": noisy_query,
                "is_in_domain": True,
                "actual_sector": sector,
                "query_type": "abbreviation"
            })
            query_id += 1
        
        # Short search queries
        for i in range(short_count):
            short_query = create_short_search(sector)
            queries.append({
                "id": query_id,
                "query": short_query,
                "is_in_domain": True,
                "actual_sector": sector,
                "query_type": "short_search"
            })
            query_id += 1
    
    return queries

def generate_adversarial_ood_queries() -> List[Dict]:
    """Generate 200 Adversarial OOD queries (B2B format, non-target sectors)."""
    queries = []
    query_id = 701  # Starting after in-domain
    
    for i in range(200):
        seed = ADVERSARIAL_OOD_SEEDS[i % len(ADVERSARIAL_OOD_SEEDS)]
        # Add some noise to make it more realistic
        if random.random() < 0.2:
            seed = add_typo_noise(seed)
        if random.random() < 0.15:
            seed = add_abbreviation_noise(seed)
        
        queries.append({
            "id": query_id,
            "query": seed,
            "is_in_domain": False,
            "actual_sector": "OOD",
            "query_type": "adversarial_ood"
        })
        query_id += 1
    
    return queries

def generate_b2c_noise_queries() -> List[Dict]:
    """Generate 100 B2C/General noise queries."""
    queries = []
    query_id = 901  # Starting after adversarial OOD
    
    for i in range(100):
        seed = B2C_NOISE_SEEDS[i % len(B2C_NOISE_SEEDS)]
        # Add minimal noise for realism
        if random.random() < 0.1:
            seed = add_typo_noise(seed)
        
        queries.append({
            "id": query_id,
            "query": seed,
            "is_in_domain": False,
            "actual_sector": "OOD",
            "query_type": "b2c_noise"
        })
        query_id += 1
    
    return queries

def main():
    """Generate complete benchmark dataset."""
    print("Generating B2B Sector Intent Router Stress Test Dataset...")
    
    # Generate all query types
    in_domain = generate_in_domain_queries()
    adversarial_ood = generate_adversarial_ood_queries()
    b2c_noise = generate_b2c_noise_queries()
    
    # Combine all queries
    all_queries = in_domain + adversarial_ood + b2c_noise
    
    # Shuffle for randomness
    random.shuffle(all_queries)
    
    # Reassign IDs after shuffle
    for i, query in enumerate(all_queries, 1):
        query["id"] = i
    
    # Statistics
    in_domain_count = sum(1 for q in all_queries if q["is_in_domain"])
    ood_count = len(all_queries) - in_domain_count
    
    sector_distribution = {}
    for q in all_queries:
        if q["is_in_domain"]:
            sector_distribution[q["actual_sector"]] = sector_distribution.get(q["actual_sector"], 0) + 1
    
    query_type_distribution = {}
    for q in all_queries:
        query_type_distribution[q["query_type"]] = query_type_distribution.get(q["query_type"], 0) + 1
    
    print(f"\nDataset Statistics:")
    print(f"Total Queries: {len(all_queries)}")
    print(f"In-Domain (B2B): {in_domain_count}")
    print(f"Out-of-Domain (OOD): {ood_count}")
    print(f"\nSector Distribution (In-Domain):")
    for sector, count in sector_distribution.items():
        print(f"  {sector}: {count}")
    print(f"\nQuery Type Distribution:")
    for qtype, count in query_type_distribution.items():
        print(f"  {qtype}: {count}")
    
    # Save to JSON file
    output_file = "benchmark_dataset_1000.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_queries, f, ensure_ascii=False, indent=2)
    
    print(f"\nDataset saved to: {output_file}")
    print("✓ Benchmark dataset generation complete!")

if __name__ == "__main__":
    main()
