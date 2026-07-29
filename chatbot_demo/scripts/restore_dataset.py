import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"

def main():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    original_recs = [r for r in data["kayitlar"] if r["id"] <= 776]
    data["kayitlar"] = original_recs
    DATASET_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Restored dataset to {len(original_recs)} records.")

if __name__ == "__main__":
    main()
