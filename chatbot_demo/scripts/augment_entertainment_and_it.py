import json
from pathlib import Path

ROOT = Path("c:/Users/AZRA/OneDrive/Desktop/Chatbot_Bilgi_Merkezi_Projesi/chatbot_demo")
RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
CLEAN_PATH = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
AUG_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

# Turkish prefixes and suffixes
TR_PREFIXES = ["", "acil ", "lütfen ", "şirketimiz için ", "yeni ", "kurumsal "]
TR_SUFFIXES = [" sistemi", " yazılımı", " altyapısı", " platformu", " çözümü", " entegrasyonu"]

# English prefixes and suffixes
EN_PREFIXES = ["", "we need ", "looking for ", "we are looking for ", "urgent ", "enterprise "]
EN_SUFFIXES = [" system", " software", " infrastructure", " platform", " solution", " integration"]

# Entertainment base phrases
ENT_TR_PHRASES = [
    "konser bilet satış",
    "festival geçiş kontrol",
    "etkinlik biletleme",
    "tiyatro koltuk rezervasyon",
    "nfc wristband ödeme",
    "müze turnike geçiş",
    "eğlence parkı biletleme",
    "etkinlik yönetim portalı",
    "sinema koltuk rezervasyon",
    "fuar ziyaretçi takip"
]

ENT_EN_PHRASES = [
    "digital ticketing",
    "event ticketing",
    "concert seat booking",
    "festival access control",
    "nfc ticketing and entry",
    "museum gate ticket",
    "theme park reservation",
    "venue ticket sales",
    "stadium seat reservation",
    "entertainment event management"
]

# IT base phrases
IT_TR_PHRASES = [
    "DevOps otomasyon",
    "CI/CD boru hattı",
    "bulut altyapı yönetimi",
    "siber güvenlik ve sızma testi",
    "veri merkezi sunucu",
    "güvenlik duvarı firewall",
    "api entegrasyon ve backend",
    "veritabanı cloud göçü",
    "sistem izleme ve monitoring",
    "ağ güvenliği network"
]

IT_EN_PHRASES = [
    "DevOps automation",
    "CI/CD pipeline setup",
    "cloud infrastructure provisioning",
    "cybersecurity pentesting",
    "server infrastructure backup",
    "firewall setup network security",
    "api gateway backend engineering",
    "database migration cloud",
    "system log monitoring metrics",
    "network firewall routing"
]

def generate_records(phrases, prefixes, suffixes, lang, sector, start_id):
    records = []
    current_id = start_id
    existing_msgs = set()
    for phrase in phrases:
        for pref in prefixes:
            for suff in suffixes:
                msg = f"{pref}{phrase}{suff}".strip()
                # Clean multiple spaces
                msg = " ".join(msg.split())
                if len(msg) < 5 or msg.lower() in existing_msgs:
                    continue
                existing_msgs.add(msg.lower())
                
                records.append({
                    "id": current_id,
                    "mesaj": msg,
                    "lang": lang,
                    "beklenen_sektor": sector,
                    "beklenen_mod": "K2",
                    "zorluk": "augmented_prefix_suffix",
                    "varyant": "prefix_suffix",
                    "prefix": pref.strip(),
                    "suffix": suff.strip(),
                    "ham_mesaj": msg,
                    "normalize_mesaj": msg.lower()
                })
                current_id += 1
    return records

def main():
    print("Generating Entertainment and IT records...")
    
    # Generate Entertainment
    ent_tr = generate_records(ENT_TR_PHRASES, TR_PREFIXES, TR_SUFFIXES, "tr", "eglence", 200000)
    ent_en = generate_records(ENT_EN_PHRASES, EN_PREFIXES, EN_SUFFIXES, "en", "eglence", 210000)
    ent_records = ent_tr + ent_en
    print(f"Generated {len(ent_records)} Entertainment records.")
    
    # Generate IT
    it_tr = generate_records(IT_TR_PHRASES, TR_PREFIXES, TR_SUFFIXES, "tr", "bilisim", 300000)
    it_en = generate_records(IT_EN_PHRASES, EN_PREFIXES, EN_SUFFIXES, "en", "bilisim", 310000)
    it_records = it_tr + it_en
    print(f"Generated {len(it_records)} IT records.")
    
    # Load raw dataset
    if RAW_PATH.exists():
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        raw_recs = raw_data.get("kayitlar", [])
        
        # Remove old augmented ent/it from raw dataset if any to avoid duplication
        raw_recs = [r for r in raw_recs if not (isinstance(r.get("id"), int) and r.get("id", 0) >= 200000)]
        
        # Append new records
        raw_recs.extend(ent_records[:120])  # Add subset to raw (we don't need all 300+ in raw, but let's keep it clean)
        raw_recs.extend(it_records[:120])
        
        raw_data["kayitlar"] = raw_recs
        with open(RAW_PATH, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        print("Updated raw dataset.")

    # Load clean dataset
    if CLEAN_PATH.exists():
        with open(CLEAN_PATH, "r", encoding="utf-8") as f:
            clean_data = json.load(f)
        clean_recs = clean_data.get("kayitlar", [])
        clean_recs = [r for r in clean_recs if not (isinstance(r.get("id"), int) and r.get("id", 0) >= 200000)]
        clean_recs.extend(ent_records[:120])
        clean_recs.extend(it_records[:120])
        clean_data["kayitlar"] = clean_recs
        with open(CLEAN_PATH, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        print("Updated clean dataset.")

    # Load augmented dataset
    if AUG_PATH.exists():
        with open(AUG_PATH, "r", encoding="utf-8") as f:
            aug_data = json.load(f)
        aug_recs = aug_data.get("kayitlar", [])
        aug_recs = [r for r in aug_recs if not (isinstance(r.get("id"), int) and r.get("id", 0) >= 200000)]
        
        # For augmented we add more to reach the desired target size
        aug_recs.extend(ent_records[:150])
        aug_recs.extend(it_records[:150])
        
        aug_data["kayitlar"] = aug_recs
        with open(AUG_PATH, "w", encoding="utf-8") as f:
            json.dump(aug_data, f, ensure_ascii=False, indent=2)
        print("Updated augmented dataset.")

if __name__ == "__main__":
    main()
