import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

TARGET_PREFIXES = ["402_", "403_", "404_", "405_", "406_", "407_", "408_", "409_", "410_"]

def main():
    if not DATASET_PATH.exists():
        print(f"[!] Dosya bulunamadı: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Dataset structure check: root might contain 'kayitlar' wrapper
    is_wrapped = isinstance(data, dict) and "kayitlar" in data
    kayitlar = data["kayitlar"] if is_wrapped else data

    fixed_count = 0
    for item in kayitlar:
        item_id = str(item.get("id", ""))
        # 402-410 serisine ait bir ID ve ood ise düzelt
        if any(item_id.startswith(prefix) for prefix in TARGET_PREFIXES):
            if item.get("beklenen_sektor") in ("ood", "belirsiz"):
                item["beklenen_sektor"] = "egitim"
                fixed_count += 1

    # Save directly to the original file
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {fixed_count} adet kayıt 'ood' -> 'egitim' olarak güncellendi.")
    print(f"[+] Dosya kaydedildi: {DATASET_PATH.name}")

if __name__ == "__main__":
    main()
