import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

deep_tech_seeds = [
    {
        "id": "en_101_deep_it",
        "source_id": 999101,
        "lang": "en",
        "mesaj": "scalable microservices architecture kafka streaming kubernetes deployment payment gateway backend cloud software",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "scalable microservices architecture kafka streaming kubernetes deployment payment gateway backend cloud software",
        "normalize_mesaj": "scalable microservices architecture kafka streaming kubernetes deployment payment gateway backend cloud software",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    },
    {
        "id": "en_301_deep_media",
        "source_id": 999301,
        "lang": "en",
        "mesaj": "ott video platform low latency HLS video transcoding DRM content protection video streaming infrastructure",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "ott video platform low latency HLS video transcoding DRM content protection video streaming infrastructure",
        "normalize_mesaj": "ott video platform low latency HLS video transcoding DRM content protection video streaming infrastructure",
        "beklenen_sektor": "eglence",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    },
    {
        "id": "en_401_deep_health",
        "source_id": 999401,
        "lang": "en",
        "mesaj": "LIS laboratory information system software automated blood analyzers HL7 interface medical lab database integration",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "LIS laboratory information system software automated blood analyzers HL7 interface medical lab database integration",
        "normalize_mesaj": "LIS laboratory information system software automated blood analyzers HL7 interface medical lab database integration",
        "beklenen_sektor": "saglik",
        "beklenen_mod": "K2",
        "zorluk": "dogrudan"
    }
]

def main():
    if not DATASET_PATH.exists():
        print(f"[!] Dosya bulunamadı: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check structure
    is_wrapped = isinstance(data, dict) and "kayitlar" in data
    kayitlar = data["kayitlar"] if is_wrapped else data

    # Evade duplicates
    existing_ids = {r.get("id") for r in kayitlar}
    added_count = 0

    for seed in deep_tech_seeds:
        if seed["id"] not in existing_ids:
            kayitlar.append(seed)
            added_count += 1

    if is_wrapped:
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} yeni Deep-Tech İngilizce çapa kaydı eklendi.")
    print(f"[+] Re-indexing başlatılıyor...")

    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Re-indexing başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
