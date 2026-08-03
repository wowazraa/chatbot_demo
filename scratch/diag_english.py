import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from src.v2_pipeline import V2IntentPipeline

# Pipeline'i baslatiyoruz
pipeline = V2IntentPipeline()
pipeline._ensure_store()

test_sentences = [
    # 1. Bilişim (Cloud/Microservices)
    "We are migrating our legacy monolith to a microservices architecture on AWS.",
    # 5. Eğlence (Streaming/Esports)
    "Our esports tournament requires a low-latency live streaming backend with real-time chat."
]

print("============================================================")
print(" DIAGNOSTIC TEST (BİLİŞİM & EĞLENCE İÇİN TOP-5 HITS)")
print("============================================================")

for text in test_sentences:
    print(f"\nGİRDİ:  {text}")
    
    # 1) Metni vektorize edip ham 'hits' dökümünü almak istiyoruz.
    q_vec = pipeline._embed_query(text)
    hits = pipeline.store.search(q_vec, top_k=5)
    
    print("--- Ham Top-5 Hits ---")
    for i, h in enumerate(hits):
        print(f"  {i+1}) [{h.sector}] {h.text_content[:50]} (Score: {float(h.score):.4f})")
    
    # 2) Pipeline çalışmasını görelim
    res = pipeline.run(text)
    print("--- Pipeline Kararı ---")
    print(f"Hedef: {res.sector}, Mod: {res.layer}, Güven Skoru: {res.confidence_score:.4f}")

print("\n============================================================")
