import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

chitchat_seeds = [
    # TR
    {"mesaj": "günaydın nasılsınız", "lang": "tr"},
    {"mesaj": "iyi günler dilerim kolay gelsin", "lang": "tr"},
    {"mesaj": "sisteminiz nasıl çalışıyor bilgi verebilir misiniz", "lang": "tr"},
    {"mesaj": "orada kimse var mı", "lang": "tr"},
    {"mesaj": "bana yardım edebilir misin", "lang": "tr"},
    {"mesaj": "ne iş yapıyorsunuz", "lang": "tr"},
    {"mesaj": "kullanıcı yorumları nasıl", "lang": "tr"},
    {"mesaj": "iletişim numaranız var mı", "lang": "tr"},
    # EN
    {"mesaj": "good morning how are you today", "lang": "en"},
    {"mesaj": "good day hope you are doing well", "lang": "en"},
    {"mesaj": "is anyone available to chat", "lang": "en"},
    {"mesaj": "can you tell me more about your company", "lang": "en"},
    {"mesaj": "what kind of services do you offer", "lang": "en"},
    {"mesaj": "who is the founder of this platform", "lang": "en"},
    {"mesaj": "what are your support hours", "lang": "en"}
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
    for idx, seed in enumerate(chitchat_seeds):
        seed_id = f"chitchat_seed_{idx}"
        if seed_id not in existing_ids:
            new_record = {
                "id": seed_id,
                "source_id": 999990 + idx,
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

    print(f"[+] Başarıyla {added_count} adet genel sohbet/chitchat çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
