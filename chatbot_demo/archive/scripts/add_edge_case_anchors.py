import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

edge_case_seeds = [
    {
        "id": "edge_case_virus_tr",
        "source_id": 999970,
        "lang": "tr",
        "mesaj": "bizim dukkanın bilgisayarlara virüs bulaştı temizleme programı ve güvenlik yazılımı",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "bizim dukkanın bilgisayarlara virüs bulaştı temizleme programı ve güvenlik yazılımı",
        "normalize_mesaj": "bizim dukkanın bilgisayarlara virüs bulaştı temizleme programı ve güvenlik yazılımı",
        "beklenen_sektor": "bilisim",
        "beklenen_mod": "K2",
        "zorluk": "dolayli"
    },
    {
        "id": "edge_case_kvkk_tr",
        "source_id": 999971,
        "lang": "tr",
        "mesaj": "açık rıza metinleri ve kvkk uyumlu hastane biyometrik kimlik doğrulama hasta kayıt sistemi",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "açık rıza metinleri ve kvkk uyumlu hastane biyometrik kimlik doğrulama hasta kayıt sistemi",
        "normalize_mesaj": "açık rıza metinleri ve kvkk uyumlu hastane biyometrik kimlik doğrulama hasta kayıt sistemi",
        "beklenen_sektor": "saglik",
        "beklenen_mod": "K2",
        "zorluk": "dolayli"
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
    for seed in edge_case_seeds:
        if seed["id"] not in existing_ids:
            kayitlar.append(seed)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet edge-case çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
