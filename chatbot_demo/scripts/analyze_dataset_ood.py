import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset path not found: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", data) if isinstance(data, dict) else data
    
    print(f"=== GENEL VERİ SETİ ÖZETİ ===")
    print(f"Toplam Kayıt Sayısı: {len(kayitlar)}")
    
    # Dil Dağılımı
    langs = Counter(r.get("lang", "tr") for r in kayitlar)
    print(f"Dil Dağılımı: {dict(langs)}")
    
    # Sektör Dağılımı (Genel)
    sectors = Counter(r.get("beklenen_sektor", "belirsiz") for r in kayitlar)
    print(f"\nSektör Dağılımı (Genel):")
    for sec, count in sectors.items():
        print(f"  - {sec}: {count}")

    # Sektör Dağılımı (İngilizce Kayıtlar)
    en_records = [r for r in kayitlar if r.get("lang") == "en"]
    en_sectors = Counter(r.get("beklenen_sektor", "belirsiz") for r in en_records)
    print(f"\nİngilizce Kayıtların Sektör Dağılımı:")
    for sec, count in en_sectors.items():
        print(f"  - {sec}: {count}")

    # İngilizce OOD (belirsiz/ood) Kayıtların Detaylı Listesi
    print(f"\n=== İNGİLİZCE OOD / BELİRSİZ KAYITLAR (İlk 30 Örnek) ===")
    en_ood_records = [r for r in en_records if r.get("beklenen_sektor") in ("ood", "belirsiz")]
    print(f"Toplam İngilizce OOD Kayıt Sayısı: {len(en_ood_records)}")
    
    for i, r in enumerate(en_ood_records[:30]):
        print(f"[{i+1}] ID: {r.get('id')} | Mesaj: {r.get('mesaj')} | Zorluk: {r.get('zorluk', '')}")

    # Yanlışlıkla OOD olarak etiketlenmiş olabilecek (anahtar kelime analizi) kayıtlar
    print(f"\n=== POTANSİYEL YANLIŞ OOD ETİKETLERİ (Sektörel Terim İçeren OOD'ler) ===")
    
    keywords = {
        "bilisim": ["api", "saas", "cloud", "server", "cybersecurity", "software", "development", "it", "integration"],
        "saglik": ["patient", "clinic", "hospital", "doctor", "medical", "appointment", "prescription", "consultation"],
        "egitim": ["student", "lms", "school", "exam", "course", "training", "academy", "learn"],
        "turizm": ["hotel", "booking", "reservation", "travel", "flight", "tourism", "hospitality"],
        "eglence": ["event", "ticket", "streaming", "game", "concert", "festival", "entertainment"]
    }
    
    potential_fixes = 0
    for r in en_ood_records:
        msg_lower = r.get("mesaj", "").lower()
        matched_sectors = []
        for sec, words in keywords.items():
            matches = [w for w in words if w in msg_lower]
            if len(matches) >= 2: # En az 2 sektörel kelime geçiyorsa
                matched_sectors.append((sec, matches))
        
        if matched_sectors:
            potential_fixes += 1
            print(f"ID: {r.get('id')} | Mesaj: {r.get('mesaj')}")
            for sec, matches in matched_sectors:
                print(f"  -> Sektör İpucu: {sec} (Eşleşenler: {matches})")
                
    print(f"\nToplam Potansiyel Yanlış OOD Tespiti: {potential_fixes}")

if __name__ == "__main__":
    main()
