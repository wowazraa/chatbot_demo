import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        return

    with open(SCENARIOS_PATH := ROOT / "tests" / "adversarial_scenarios.json", "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", data) if isinstance(data, dict) else data
    existing_ids = {r.get("id") for r in kayitlar}
    
    added_count = 0
    for idx, sc in enumerate(scenarios):
        sc_id = f"adv_seed_{sc['test_id']}"
        if sc_id not in existing_ids:
            new_record = {
                "id": sc_id,
                "source_id": 999900 + idx,
                "lang": "en" if "en" in sc["test_id"] or any(ord(c) < 128 for c in sc["input_query"]) and "değil" not in sc["input_query"] else "tr",
                "mesaj": sc["input_query"],
                "varyant": "duz",
                "prefix": "",
                "suffix": "",
                "ham_mesaj": sc["input_query"],
                "normalize_mesaj": sc["input_query"].lower(),
                "beklenen_sektor": sc["expected_sector"],
                "beklenen_mod": "K2",
                "zorluk": "zor"
            }
            kayitlar.append(new_record)
            added_count += 1

    if isinstance(data, dict):
        data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[+] Başarıyla {added_count} adet adversarial çapa kaydı veri setine eklendi.")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
