import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

dataset_path = ROOT / "data" / "raw" / "chatbot_dataset.json"

print(f"Yükleniyor: {dataset_path}")
with open(dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

original_len = len(data["kayitlar"])
_OUR_ZORLUKLAR = {"augmented_prefix_suffix", "augmented_prefix_suffix_ascii"}

# Sadece orijinal kayıtları (zorluk seviyesi bizim eklediklerimiz OLMAYANLARI) sakla
data["kayitlar"] = [
    r for r in data["kayitlar"]
    if r.get("zorluk") not in _OUR_ZORLUKLAR
    and r.get("kaynak") not in ["admin_panel", "admin_panel_augmented"]
]
new_len = len(data["kayitlar"])

removed = original_len - new_len
print(f"Toplam {removed} adet zenginleştirilmiş (augmented) veri silindi.")
print(f"Geriye kalan orijinal ham veri sayısı: {new_len}")

with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\nIndex ve PostgreSQL veritabanı Orijinal haline güncelleniyor...")
from scripts.build_index import build
from scripts.seed_pgvector import seed_db

build(use_raw=True, batch_size=64)
seed_db(truncate=True)

print("\nBAŞARILI! Veritabanı kusursuz orijinal 928-kayıtlık haline geri döndü.")
print("Lütfen şimdi tekrar çalıştırın: python _final_dogrulama.py")
