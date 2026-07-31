import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "chatbot_dataset.json"

def restore():
    print("Orijinal veri seti geri getiriliyor...")
    
    if not RAW_FILE.exists():
        print(f"HATA: {RAW_FILE} bulunamadı!")
        return

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", data) if isinstance(data, dict) else data

    print(f"Okunan toplam kayıt: {len(kayitlar)}")

    # Sadece orijinal zorluk seviyelerine sahip olanları tut (augmented olanları at)
    orijinal_kayitlar = [
        k for k in kayitlar 
        if k.get("zorluk") not in ("augmented_prefix_suffix", "augmented_prefix_suffix_ascii")
    ]

    print(f"Filtreleme sonrası orijinal kayıt sayısı: {len(orijinal_kayitlar)}")

    # Geri yaz
    if isinstance(data, dict) and "kayitlar" in data:
        data["kayitlar"] = orijinal_kayitlar
        out_data = data
    else:
        out_data = orijinal_kayitlar

    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    print(f"BAŞARILI: Orijinal temiz veri seti {RAW_FILE} üzerine yazıldı.")

if __name__ == "__main__":
    restore()
