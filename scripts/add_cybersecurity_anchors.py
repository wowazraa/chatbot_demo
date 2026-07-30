import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

cyber_seeds = [
    {
        "id": "cyber_seed_01",
        "source_id": 999960,
        "lang": "en",
        "mesaj": "cyber security stuff for small biz B2B network firewall protection security software",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "cyber security stuff for small biz B2B network firewall protection security software",
        "normalize_mesaj": "cyber security stuff for small biz b2b network firewall protection security software",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    },
    {
        "id": "cyber_seed_02",
        "source_id": 999961,
        "lang": "en",
        "mesaj": "cybersecurity solutions enterprise endpoint protection SIEM monitoring software",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "cybersecurity solutions enterprise endpoint protection SIEM monitoring software",
        "normalize_mesaj": "cybersecurity solutions enterprise endpoint protection siem monitoring software",
        "beklenen_sektor": "bilisim",
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
    for seed in cyber_seeds:
        if seed["id"] not in existing_ids:
            kayitlar.append(seed)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet genel siber güvenlik çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
