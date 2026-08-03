import sys
import json
import uuid

# Yolları ekle
sys.path.append("C:/Users/AZRA/OneDrive/Desktop/Chatbot_Bilgi_Merkezi_Projesi/chatbot_demo")
from src.v2_pipeline import V2IntentPipeline

def test_pipeline():
    pipeline = V2IntentPipeline()
    session_id = str(uuid.uuid4())
    
    print("--- 1. HAFIZA (Takip Sorusu) Testi ---")
    res1 = pipeline.run("eğitim sektöründe okul yönetim sistemi arıyoruz", session_id=session_id)
    print(f"Q1: 'eğitim sektöründe okul yönetim sistemi arıyoruz'")
    print(f"Sektör: {res1.sector} (Confidence: {res1.confidence_score}, Layer: {res1.layer})")
    
    res2 = pipeline.run("başka neler sunuyorsunuz?", session_id=session_id)
    print(f"Q2: 'başka neler sunuyorsunuz?'")
    print(f"Sektör: {res2.sector} (Confidence: {res2.confidence_score}, Layer: {res2.layer})")
    
    print("\n--- 2. Doğal Dil Suffix Testi ---")
    test_queries = [
        "sağlık sektörüyle ilgileniyorum",
        "sağlık hakkında bilgi almak istiyorum",
        "turizm sektörü hakkında bilgi almak istiyorum",
        "bilişim hizmetleri ile ilgileniyorum"
    ]
    for q in test_queries:
        res = pipeline.run(q, session_id=str(uuid.uuid4()))
        print(f"Q: '{q}' -> Sektör: {res.sector} (Confidence: {res.confidence_score}, Layer: {res.layer})")

    print("\n--- 3. Negatif (Over-trigger) Testi ---")
    neg_queries = [
        "sağlık sektöründe personel arıyoruz",
        "eğitim sektöründe iş ortaklığı yapmak istiyoruz",
        "turizm sektöründe ofisimiz var"
    ]
    for q in neg_queries:
        res = pipeline.run(q, session_id=str(uuid.uuid4()))
        print(f"Q: '{q}' -> Sektör: {res.sector} (Confidence: {res.confidence_score}, Layer: {res.layer})")

if __name__ == '__main__':
    test_pipeline()
