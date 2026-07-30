import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

acronym_seeds = [
    {
        "id": "acronym_pacs",
        "source_id": 999950,
        "lang": "en",
        "mesaj": "PACS picture archiving and communication system medical imaging software",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "PACS picture archiving and communication system medical imaging software",
        "normalize_mesaj": "pacs picture archiving and communication system medical imaging software",
        "beklenen_sektor": "saglik",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    },
    {
        "id": "acronym_pms",
        "source_id": 999951,
        "lang": "en",
        "mesaj": "PMS property management system hotel reservation reception automation software",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "PMS property management system hotel reservation reception automation software",
        "normalize_mesaj": "pms property management system hotel reservation reception automation software",
        "beklenen_sektor": "turizm",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    }
]

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", data) if isinstance(data, dict) else data
    existing_ids = {r.get("id") for r in kayitlar}
    
    added_count = 0
    for seed in acronym_seeds:
        if seed["id"] not in existing_ids:
            kayitlar.append(seed)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet akronim çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
