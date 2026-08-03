import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

dataset_path = ROOT / "data" / "raw" / "chatbot_dataset.json"

print(f"[1] Yükleniyor: {dataset_path}")
with open(dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

original_len = len(data["kayitlar"])
data["kayitlar"] = [
    r for r in data["kayitlar"]
    if r.get("kaynak") not in ["admin_panel", "admin_panel_augmented"]
]
new_len = len(data["kayitlar"])

removed = original_len - new_len
print(f"[2] Test betiğinden gelen {removed} adet deneme kaydı silindi.")

with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("[3] Index ve PostgreSQL veritabanı eski (orijinal) haline güncelleniyor...")
from scripts.build_index import build
from scripts.seed_pgvector import seed_db

build(use_raw=True, batch_size=64)
seed_db(truncate=True)

print("\nBAŞARILI! Test kayıtları silindi ve veritabanı orijinal haline geri döndü.")
print("Lütfen şimdi tekrar çalıştırın: python _final_dogrulama.py")
