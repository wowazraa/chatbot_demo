import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
CLEAN_PATH = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
AUG_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

NEW_DOMAIN_SAMPLES = [
    # 1. Tele-tıp / Poliklinik Altyapısı (saglik)
    {"mesaj": "Poliklinigimiz icin tele-tip altyapisi ariyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 2.0},
    {"mesaj": "Polikliniklerimiz için uzaktan muayene ve tele-tıp çözümleri istemekteyiz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Özel poliklinik için teletıp portalı ve randevu altyapısı kurmak istiyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Tele-tıp altyapısı ve görüntülü hekim görüşme platformu arıyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Poliklinik yönetimi ve uzaktan sağlık altyapısı tedariği.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Telemedicine altyapısı ve poliklinik hasta görüşme sistemi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Hastane ve poliklinik ağımız için güvenli teletıp yazılımı.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Poliklinik randevu ve tele-tıp entegrasyon çözümleri.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Teletıp yazılımı ve poliklinik canlı muayene altyapısı.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Poliklinik hastaları için uzaktan teşhis ve tele-tıp sistemi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Kurumsal teletıp platformu ve poliklinik modülü gereksinimi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Poliklinik otomasyonu ile entegre tele-tıp altyapı projesi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},

    # 2. Kayıt Sistemi + Okul (egitim)
    {"mesaj": "Okulumuz icin kayit sistemi lazim.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 2.0},
    {"mesaj": "Okul ve kolej için öğrenci kayıt sistemi ve harç takip yazılımı arıyoruz.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Özel okulumuz için yeni dönem kayıt sistemi projesi.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Okullar için ders seçim ve online kayıt altyapısı tedariği.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Kolej ve okulumuza öğrenci başvuru ve kayıt otomasyonu lazım.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Okul öğrenci işleri kayıt sistemi ve numara verme yazılımı.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Anaokulu ve ilkokul için kayıt takip altyapısı teklifi almak istiyoruz.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Okul yönetiminde veli başvuru ve kayıt sistemi yazılımı.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Kolejimiz için öğrenci ön kayıt ve kesin kayıt sistemi.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Okul bünyesinde kullanılacak kayıt otomasyon çözümü.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Eğitim kurumumuz okulumuz için dijital kayıt altyapısı projesi.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Okul kayıt ve sınıf dağıtım yazılımı geliştirmek istiyoruz.", "lang": "tr", "beklenen_sektor": "egitim", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},

    # 3. Otomasyon + Klinik / Sağlık Otomasyonu (saglik)
    {"mesaj": "Saglik sektorunde otomasyon projeleri gelistiriyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 2.0},
    {"mesaj": "Sağlık sektöründe klinik otomasyon projeleri ve yazılım desteği arıyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Hastane ve klinik otomasyon sistemleri geliştirmek için teklif istiyoruz.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Klinikler için süreç otomasyonu ve sağlık veritabanı yazılımı.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.8},
    {"mesaj": "Tıp merkezi ve klinik bünyesinde hasta kabul otomasyon sistemi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Sağlık alanında laboratuvar ve klinik otomasyon yazılımları.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Özel klinik zinciri için operasyonel otomasyon ve randevu yazılımı.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Sağlık kuruluşları için dijital klinik otomasyonu entegrasyonu.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Diş kliniği ve tıbbi merkezler için iş akışı otomasyon sistemi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Sağlık sektörüne yönelik yerli klinik otomasyon çözümleri.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5},
    {"mesaj": "Klinik muayene ve tıbbi reçete otomasyon yazılımı gereksinimi.", "lang": "tr", "beklenen_sektor": "saglik", "beklenen_mod": "K2", "zorluk": "dogrudan", "weight": 1.5}
]

def update_file(path, is_augmented=False):
    if not path.exists():
        print(f"[!] Dosya bulunamadı: {path}")
        return
        
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
        
    records = data.get("kayitlar", data) if isinstance(data, dict) else data
    existing = {r["mesaj"].lower().strip() for r in records if "mesaj" in r}
    
    added_count = 0
    if is_augmented:
        max_id_prefix = "8888_"
        idx = 1
        for s in NEW_DOMAIN_SAMPLES:
            if s["mesaj"].lower().strip() not in existing:
                record = {
                    "id": f"{max_id_prefix}{idx}",
                    "source_id": 88888,
                    "lang": s["lang"],
                    "mesaj": s["mesaj"],
                    "varyant": "duz",
                    "prefix": "",
                    "suffix": "",
                    "ham_mesaj": s["mesaj"],
                    "normalize_mesaj": s["mesaj"],
                    "beklenen_sektor": s["beklenen_sektor"],
                    "beklenen_mod": s["beklenen_mod"],
                    "zorluk": s["zorluk"],
                    "weight": s.get("weight", 1.0)
                }
                records.append(record)
                idx += 1
                added_count += 1
    else:
        max_id = 88000
        for r in records:
            if isinstance(r.get("id"), int) and r["id"] >= max_id:
                max_id = r["id"]
        for s in NEW_DOMAIN_SAMPLES:
            if s["mesaj"].lower().strip() not in existing:
                max_id += 1
                record = {
                    "id": max_id,
                    "mesaj": s["mesaj"],
                    "lang": s["lang"],
                    "beklenen_sektor": s["beklenen_sektor"],
                    "beklenen_mod": s["beklenen_mod"],
                    "zorluk": s["zorluk"],
                    "weight": s.get("weight", 1.0)
                }
                records.append(record)
                added_count += 1
                
    if isinstance(data, dict):
        data["kayitlar"] = records
    else:
        data = records
        
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Güncellendi: {path.name} (+{added_count} yeni kayıt, Toplam: {len(records)})")

if __name__ == "__main__":
    update_file(RAW_PATH, is_augmented=False)
    update_file(CLEAN_PATH, is_augmented=False)
    update_file(AUG_PATH, is_augmented=True)
