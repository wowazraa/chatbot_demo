import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"

PREFIXES = [
    "",
    "lütfen ",
    "acil ",
    "şirketimiz için ",
    "bizim için ",
    "yeni kuracağımız ",
    "hızlıca "
]

SUFFIXES = [
    "",
    " arıyoruz.",
    " istiyoruz.",
    " lazım.",
    " gerekiyor.",
    " entegrasyonu istiyoruz.",
    " entegrasyonu gerekiyor.",
    " kurmak istiyoruz.",
    " platformu gerekiyor."
]

# Kök ifadeler ve beklenen sektörler
BASE_PHRASES = {
    "sağlık": [
        "hekim takvimi",
        "muayene yönetim sistemi",
        "tele-tıp çözümleri",
        "uzaktan sağlık asistanı",
        "hekim takvimi ve muayene kaydı",
        "poliklinik için tele-tıp altyapısı"
    ],
    "turizm": [
        "travel agency booking",
        "check-in çözümü",
        "turizmle uğraşan işletmeler için otomasyon",
        "otel yönetim yazılımı teklifi",
        "tatil köyü online rezervasyon altyapısı",
        "tatil köyü için online rezervasyon",
        "otel yönetim yazılımı"
    ],
    "savunma": [
        "NATO standartlarında güvenli mesajlaşma",
        "birlikler arası kriptolu haberleşme",
        "NATO standartlarında güvenli haberleşme",
        "askeri güvenli mesajlaşma"
    ]
}

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}")
        return

    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    kayitlar = data["kayitlar"]
    print(f"Mevcut kayıt sayısı: {len(kayitlar)}")

    existing_messages = {r["mesaj"].lower().strip() for r in kayitlar}
    max_id = max(r["id"] for r in kayitlar)

    added_count = 0
    new_records = []

    for sektor, phrases in BASE_PHRASES.items():
        for phrase in phrases:
            for prefix in PREFIXES:
                for suffix in SUFFIXES:
                    # Kombinasyon oluştur
                    mesaj = f"{prefix}{phrase}{suffix}"
                    # Fazla boşlukları temizle
                    mesaj = " ".join(mesaj.split()).strip()
                    
                    if not mesaj:
                        continue
                    
                    # Eğer zaten varsa ekleme
                    mesaj_lower = mesaj.lower()
                    if mesaj_lower in existing_messages:
                        continue
                    
                    existing_messages.add(mesaj_lower)
                    max_id += 1
                    
                    # Lang belirleme (travel agency gibi İngilizce ifadeler için "en")
                    lang = "en" if any(word in mesaj_lower for word in ["booking", "agency", "travel"]) else "tr"
                    
                    record = {
                        "id": max_id,
                        "mesaj": mesaj,
                        "lang": lang,
                        "beklenen_sektor": sektor,
                        "beklenen_mod": "K2",
                        "zorluk": "dogrudan"
                    }
                    new_records.append(record)
                    added_count += 1

    print(f"Türetilen yeni benzersiz kayıt sayısı: {added_count}")
    
    # Dataset'e ekle ve kaydet
    data["kayitlar"] = kayitlar + new_records
    DATASET_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Yeni toplam kayıt sayısı: {len(data['kayitlar'])}")
    print("Dataset başarıyla güncellendi.")

if __name__ == "__main__":
    main()
