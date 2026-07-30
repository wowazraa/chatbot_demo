import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

how_are_you_seeds = [
    # TR
    {"mesaj": "nasılsın", "lang": "tr"},
    {"mesaj": "nasılsınız", "lang": "tr"},
    {"mesaj": "naber", "lang": "tr"},
    {"mesaj": "ne haber", "lang": "tr"},
    {"mesaj": "nehaber nasılsın", "lang": "tr"},
    # EN
    {"mesaj": "how are you", "lang": "en"},
    {"mesaj": "how are you doing", "lang": "en"},
    {"mesaj": "how is it going", "lang": "en"},
    {"mesaj": "hows it going", "lang": "en"},
    {"mesaj": "whats up", "lang": "en"},
    {"mesaj": "whatsup how are you doing", "lang": "en"}
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
    for idx, seed in enumerate(how_are_you_seeds):
        seed_id = f"how_are_you_seed_{idx}"
        if seed_id not in existing_ids:
            new_record = {
                "id": seed_id,
                "source_id": 999110 + idx,
                "lang": seed["lang"],
                "mesaj": seed["mesaj"],
                "varyant": "duz",
                "prefix": "",
                "suffix": "",
                "ham_mesaj": seed["mesaj"],
                "normalize_mesaj": seed["mesaj"].lower(),
                "beklenen_sektor": "ood",
                "beklenen_mod": "K2",
                "zorluk": "dogrudan"
            }
            kayitlar.append(new_record)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet nasılsın/how are you çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
