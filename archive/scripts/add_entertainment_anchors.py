import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

ent_seeds = [
    {
        "id": "ent_seed_festival_01",
        "source_id": 999980,
        "lang": "tr",
        "mesaj": "Açık hava festivallerimiz için NFC bileklikli temassız ödeme ve geçit otomasyonu biletleme giriş altyapısı",
        "varyant": "duz",
        "prefix": "",
        "suffix": "",
        "ham_mesaj": "Açık hava festivallerimiz için NFC bileklikli temassız ödeme ve geçit otomasyonu biletleme giriş altyapısı",
        "normalize_mesaj": "açık hava festivallerimiz için nfc bileklikli temassız ödeme ve geçit otomasyonu biletleme giriş altyapısı",
        "beklenen_sektor": "eglence",
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
    for seed in ent_seeds:
        if seed["id"] not in existing_ids:
            kayitlar.append(seed)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet eğlence festival çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
