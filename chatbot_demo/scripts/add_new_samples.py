import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
CLEAN_PATH = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
AUG_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

# New samples to add:
# 1. TR Hard OOD (masa, sandalye, vb.)
# 2. EN Positive B2B (saas vendor, custom crm, crm platform)
# 3. BI & Entegrasyon (dashboard, bi tool, powerbi, business intelligence)
NEW_SAMPLES = [
    # TR Hard OOD
    {
        "mesaj": "Ofise 50 adet ahşap masa, 100 tane ergo sandalye alacağız.",
        "lang": "tr",
        "beklenen_sektor": "ood",
        "beklenen_mod": "FB",
        "zorluk": "tuzak",
        "weight": 2.0
    },
    {
        "mesaj": "Toplantı odası için masalar, sandalyeler ve dolap yaptıracağız.",
        "lang": "tr",
        "beklenen_sektor": "ood",
        "beklenen_mod": "FB",
        "zorluk": "tuzak",
        "weight": 2.0
    },
    {
        "mesaj": "Ofis mobilyası, çalışma masası ve koltuk tedariği arıyoruz.",
        "lang": "tr",
        "beklenen_sektor": "ood",
        "beklenen_mod": "FB",
        "zorluk": "tuzak",
        "weight": 2.0
    },
    # EN Positive B2B
    {
        "mesaj": "We are looking for a B2B SaaS vendor to implement a custom CRM platform.",
        "lang": "en",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.8
    },
    {
        "mesaj": "Looking for a reliable SaaS vendor for enterprise CRM solutions.",
        "lang": "en",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.5
    },
    {
        "mesaj": "Need a third-party vendor to integrate a custom CRM system.",
        "lang": "en",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.5
    },
    # BI & Entegrasyon
    {
        "mesaj": "Mevcut ERP üzerine custom dashboard ve BI tool entegre etmek istiyoruz.",
        "lang": "tr",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.8
    },
    {
        "mesaj": "ERP verilerimizi görselleştirmek için BI dashboard entegrasyonu lazım.",
        "lang": "tr",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.5
    },
    {
        "mesaj": "Raporlama için custom dashboard ve analitik yazılımı arıyoruz.",
        "lang": "tr",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan",
        "weight": 1.5
    }
]

def update_file(path, is_augmented=False):
    if not path.exists():
        print(f"File not found: {path}")
        return
        
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
        
    records = data.get("kayitlar", data) if isinstance(data, dict) else data
    
    # Clean duplicates in new samples
    existing = {r["mesaj"].lower().strip() for r in records if "mesaj" in r}
    
    if is_augmented:
        max_id_prefix = "9999_"
        idx = 1
        for s in NEW_SAMPLES:
            if s["mesaj"].lower().strip() not in existing:
                record = {
                    "id": f"{max_id_prefix}{idx}",
                    "source_id": 99999,
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
    else:
        max_id = max(r["id"] for r in records if isinstance(r.get("id"), int))
        for s in NEW_SAMPLES:
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
                
    if isinstance(data, dict):
        data["kayitlar"] = records
    else:
        data = records
        
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Updated: {path.name} (Total records: {len(records)})")

update_file(RAW_PATH, is_augmented=False)
update_file(CLEAN_PATH, is_augmented=False)
update_file(AUG_PATH, is_augmented=True)
