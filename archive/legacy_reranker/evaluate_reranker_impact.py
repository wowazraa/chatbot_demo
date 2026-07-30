"""
Offline Evaluation: Accuracy vs Latency (Reranker Impact)
"""
import time
import sys
import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.smart_gate
from src.chatbot import Chatbot
from src.frontend import serialize_response
from src.score_fusion import FUSION_ALPHA_BGE

# Test Dataset: (query, true_sector)
TEST_DATA = [
    # 1. Karmaşık Kelimeler (Kelime Tuzağı)
    ("Askeri hastanede kalp muayenesi olmak istiyorum", "health"), 
    ("Otobüs bileti alıp turistik bir tura çıkmak, sonra da okulumun eğitimine devam etmek istiyorum", "tourism"),
    ("Askerlik tecil işlemlerimi üniversite diploması ile nasıl yapabilirim?", "education"),
    
    # 2. Reranker'ın Ezmesi Gereken OOD (Out-of-Domain) Cümleler (BGE'yi Yanıltanlar)
    ("Savunma sanayi hisse senedi fiyatları ne kadar oldu?", "ood"),
    ("Bugün hastanenin önünde çok büyük bir trafik kazası olmuş", "ood"),
    ("Eğitim uçakları ve savaş jetleri için oyun bilgisayarı toplamak istiyorum", "ood"),
    
    # 3. Zayıf Bağlam / Gri Alanlar (0.75-0.85 bandı)
    ("Dün gece sürekli öksürdüm, sabaha karşı nefes alamadım", "health"),
    ("Deniz kenarında her şeyin içinde olduğu lüks bir tesis arıyorum, bütçe kısıtım yok", "tourism"),
    ("Kayıt yenileme dönemini kaçırdım, harç parasını nereye yatıracağım?", "education"),
    ("Kripto komuta ve telsiz altyapısı ihalelerine girmek istiyoruz", "defense")
]

def evaluate_router(test_dataset, bot, use_reranker=True):
    predictions = []
    latencies = []
    
    # Configure the SmartGate threshold dynamically
    original_threshold = src.smart_gate.SMART_RERANK_SKIP_THRESHOLD
    if not use_reranker:
        src.smart_gate.SMART_RERANK_SKIP_THRESHOLD = 0.00 # Always skip reranker (BGE >= 0.0)
    else:
        src.smart_gate.SMART_RERANK_SKIP_THRESHOLD = 0.85 # Restore legacy
        
    for i, (query, true_label) in enumerate(test_dataset):
        start_time = time.time()
        resp = bot.sor(query, session_id=f"eval_session_{use_reranker}_{i}")
        payload = serialize_response(resp)
        latencies.append((time.time() - start_time) * 1000) # ms
        
        pred_label = payload.get("intent_router", {}).get("intent", {}).get("sector", "ood")
        if payload.get("mod") == "FB" or payload.get("mod") == "OOD":
            pred_label = "ood"
        
        predictions.append(pred_label)
        print(f"[{'B' if use_reranker else 'A'}] Query: {query[:30]}... | True: {true_label} | Pred: {pred_label} | Score: {payload.get('skor')}")
        
    # Restore
    src.smart_gate.SMART_RERANK_SKIP_THRESHOLD = original_threshold
    
    correct = sum(1 for (true, pred) in zip([t[1] for t in test_dataset], predictions) if true == pred)
    acc = correct / len(test_dataset)
    avg_latency = sum(latencies) / len(latencies)
    return acc, avg_latency

def main():
    print("Modeller yükleniyor (BGE-M3 + Reranker)...")
    bot = Chatbot()
    # Warmup
    bot.sor("merhaba")
    
    print("-" * 50)
    print("EVALUATION BASHILIYOR...")
    print(f"Fusion Alpha: {FUSION_ALPHA_BGE} BGE / {1.0 - FUSION_ALPHA_BGE} Reranker")
    print("-" * 50)
    
    acc_a, lat_a = evaluate_router(TEST_DATA, bot, use_reranker=False)
    acc_b, lat_b = evaluate_router(TEST_DATA, bot, use_reranker=True)

    print(f"Senaryo A (Sadece BGE-M3) -> Doğruluk: %{acc_a*100:.2f} | Ortalama Latens: {lat_a:.1f} ms")
    print(f"Senaryo B (Hibrit Mimari) -> Doğruluk: %{acc_b*100:.2f} | Ortalama Latens: {lat_b:.1f} ms")
    
    acc_delta = (acc_b - acc_a) * 100
    lat_delta = lat_b - lat_a
    
    print("-" * 50)
    print("SONUÇLAR (RERANKER KAZANCI/MALİYETİ):")
    print(f"Doğruluk Kazancı (Accuracy Delta) : %{acc_delta:+.2f}")
    print(f"Hız Maliyeti     (Latency Delta)  : {lat_delta:+.1f} ms")
    if lat_b < 150.0:
        print("-> Hedef: Sub-150ms BASARILI")
    else:
        print("-> Hedef: Sub-150ms BASARISIZ")

if __name__ == "__main__":
    main()
