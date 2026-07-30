"""
Dataset Güncelleme Scripti:
1. 6 ekstra sektörü (finans, lojistik, e_ticaret, bilişim, enerji, ik_kurumsal) arşivler
2. 4 çekirdek sektör için 10 başarısız senaryo kapsamında çeşitli yeni eğitim örnekleri ekler
3. İndeksi yeniden build eder
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
ARCHIVE_PATH = ROOT / "data" / "raw" / "chatbot_dataset_arsiv_6sektor.json"

EXTRA_SEKTORLER = {"finans", "lojistik", "e_ticaret", "bilişim", "enerji", "ik_kurumsal"}
CORE_SEKTORLER  = {"sağlık", "turizm", "savunma", "eğitim"}

# ── Yeni eğitim örnekleri (10 başarısız senaryonun semantik karşılıkları) ──────
# Her biri farklı ifade, aynı anlam → BGE genellesin
YENI_ORNEKLER = [
    # --- TURIZM → B2, B4, B5, B6 ---
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Turizmle uğraşan bir şirketiz, yazılım hizmeti arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Turizm alanında faaliyet gösteren firmamız için dijital çözüm istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Tatil köyümüz için online rezervasyon ve konaklama yönetim sistemi arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Tatil tesisimiz için misafir check-in ve oda yönetim yazılımı istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Seyahat acentemiz için check-in ve rezervasyon takip çözümü arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Acente olarak tur ve uçuş rezervasyonlarını yönetecek bir platform istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Otel yönetim yazılımı almak istiyoruz, ön büro ve muhasebe entegrasyonu şart."},
    {"lang": "tr", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Otelimizin ön büro işlemlerini ve misafir takibini dijitalleştirmek istiyoruz."},
    {"lang": "en", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "We are a travel agency looking for a booking and check-in management platform."},
    {"lang": "en", "beklenen_sektor": "turizm", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Our resort needs an online reservation system with room status tracking."},

    # --- SAĞLIK → A6, A7 ---
    {"lang": "tr", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Hekim takvimi ve muayene kaydı tutacak bir klinik otomasyon sistemi arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Doktor çalışma takvimi, muayene notları ve hasta dosyası yönetimi istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Poliklinigimiz için tele-tıp altyapısı ve uzaktan hasta konsültasyon modülü lazım."},
    {"lang": "tr", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Tele-tıp ve online doktor görüşmesi sağlayacak bir sağlık platformu arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Kliniğimizde hekim programları ve poliklinik iş akışını dijitalleştirmek istiyoruz."},
    {"lang": "en", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "We need a telemedicine platform for remote patient consultations and doctor scheduling."},
    {"lang": "en", "beklenen_sektor": "sağlık", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Our polyclinic needs a physician schedule management and examination record system."},

    # --- SAVUNMA → C4, G3 ---
    {"lang": "tr", "beklenen_sektor": "savunma", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "NATO standartlarına uygun şifreli ve güvenli askeri mesajlaşma platformu arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "savunma", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Gizli veri akışı için kriptolu haberleşme altyapısı kurmak istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "savunma", "beklened_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Savunma Bakanlığı standartlarına uygun, kapalı ağda çalışan güvenli sunucu istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "savunma", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Siber saldırılara dayanıklı, izole ağda çalışabilen askeri iletişim sistemi arıyoruz."},
    {"lang": "tr", "beklenen_sektor": "savunma", "beklenen_mod": "K2", "zorluk": "uzun_kurumsal",
     "mesaj": "Milli savunma projemiz için şifreli komuta ve haberleşme altyapısı tedarik etmek istiyoruz."},
    {"lang": "en", "beklenen_sektor": "savunma", "beklened_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "We need a NATO-compliant encrypted military communication platform for classified operations."},
    {"lang": "en", "beklenen_sektor": "savunma", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Seeking a secure messaging server that operates on closed air-gapped networks for defense use."},

    # --- EĞİTİM → D5, G4 ---
    {"lang": "tr", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "LMS kurulumu için teklif almak istiyoruz, e-öğrenme altyapısı kuracağız."},
    {"lang": "tr", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Kuruma LMS platformu kurduruyoruz, içerik yönetimi ve sınav modülü gerekiyor."},
    {"lang": "tr", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Kamu kurumuna eğitim ve danışmanlık hizmeti sunuyoruz, çalışan LMS'e ihtiyacımız var."},
    {"lang": "tr", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "uzun_kurumsal",
     "mesaj": "Kamu çalışanlarına yönelik online sertifika ve e-öğrenme sistemi kurmak istiyoruz."},
    {"lang": "tr", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Personel eğitimi için uzaktan öğrenme platformu ve içerik yönetim sistemi arıyoruz."},
    {"lang": "en", "beklenen_sektor": "eğitim", "beklened_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "We are looking for an LMS platform to manage employee training and certification programs."},
    {"lang": "en", "beklenen_sektor": "eğitim", "beklenen_mod": "K2", "zorluk": "dogrudan",
     "mesaj": "Our public institution needs an e-learning and course management platform for staff training."},
]

def main():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    kayitlar = data["kayitlar"]
    print(f"[+] Mevcut kayit sayisi: {len(kayitlar)}")

    # 1) 6 ekstra sektörü arşivle
    arsiv = [r for r in kayitlar if r.get("beklenen_sektor") in EXTRA_SEKTORLER]
    core  = [r for r in kayitlar if r.get("beklenen_sektor") not in EXTRA_SEKTORLER]
    print(f"[+] Arsivlenecek (6 sektor): {len(arsiv)} kayit")
    print(f"[+] Aktif kalacak (4 sektor + belirsiz): {len(core)} kayit")

    # Arsiv dosyasini kaydet
    arsiv_data = {
        "meta": {"aciklama": "Arsivlenen 6 ekstra sektor — finans, lojistik, e_ticaret, bilisim, enerji, ik_kurumsal"},
        "kayitlar": arsiv
    }
    ARCHIVE_PATH.write_text(json.dumps(arsiv_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] Arsiv kaydedildi: {ARCHIVE_PATH}")

    # 2) Yeni ornekleri ekle
    max_id = max(r["id"] for r in kayitlar)
    yeni_kayitlar = []
    for i, ornek in enumerate(YENI_ORNEKLER, 1):
        kayit = {
            "id": max_id + i,
            "mesaj": ornek["mesaj"],
            "lang": ornek["lang"],
            "beklenen_sektor": ornek["beklenen_sektor"],
            "beklenen_mod": ornek.get("beklenen_mod", "K2"),
            "zorluk": ornek.get("zorluk", "dogrudan"),
        }
        yeni_kayitlar.append(kayit)

    core_plus_yeni = core + yeni_kayitlar
    print(f"[+] Eklenen yeni ornek sayisi: {len(yeni_kayitlar)}")
    print(f"[+] Yeni toplam: {len(core_plus_yeni)} kayit")

    # Sektor dagilimi
    from collections import Counter
    c = Counter(r.get("beklenen_sektor","") for r in core_plus_yeni)
    print("\nSektor Dagilimi:")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")

    # 3) Kaydet
    data["kayitlar"] = core_plus_yeni
    DATASET_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[+] Dataset guncellendi: {DATASET_PATH}")

if __name__ == "__main__":
    main()
