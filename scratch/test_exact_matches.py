import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from src.v2_pipeline import V2IntentPipeline

pipeline = V2IntentPipeline()
pipeline._ensure_store()

queries = [
    "sağlık", "sağlık sektörü",
    "turizm", "turizm sektörü",
    "eğitim", "eğitim sektörü",
    "bilişim", "bilişim sektörü",
    "eğlence", "eğlence sektörü",
    "health", "health sector",
    "healthcare", "healthcare sector",
    "tourism", "tourism sector",
    "education", "education sector",
    "it", "it sector",
    "technology", "technology sector",
    "entertainment", "entertainment sector"
]

print("============================================================")
print(" ÖNCEKİ DURUM: SEKTÖR KELİMELERİ VE EKLERİ")
print("============================================================")
print(f"{'GİRDİ':<30} | {'HEDEF':<15} | {'MOD'}")
print("-" * 65)

for q in queries:
    res = pipeline.run(q)
    print(f"{q:<30} | {res.sector:<15} | {res.status} ({res.layer})")
