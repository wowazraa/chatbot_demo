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
    # 2. Sağlık (Pharmacy/Prescription)
    "Need a bespoke pharmacy management system including prescription tracking.",
    # 3. Turizm (Resort/Booking)
    "We're looking for an automated check-in and dynamic pricing tool for our beachfront resort.",
    # 4. Eğitim (EdTech/Proctoring)
    "Can you develop a secure online proctoring integration for our university's LMS?",
    # 5. Eğlence (Streaming/Esports)
    "Our esports tournament requires a low-latency live streaming backend with real-time chat."
]

print("============================================================")
print(" DÜZELTMELER SONRASI: 5 YENİ İNGİLİZCE CÜMLE (GENELLEME)")
print("============================================================")
for text in test_sentences:
    # API yanit formati dict
    result = pipeline.run(text).to_intent_router()
    print(f"\nGİRDİ:  {text}")
    print(f"SLUG (URL Hedefi): [{result['target_industry']}]")
    print(f"KARAR MODU:        {result['route_type']} (Skor: {result['confidence_score']:.4f})")
    print(f"OLUŞAN URL:        {result['final_url']}")
print("\n============================================================")
