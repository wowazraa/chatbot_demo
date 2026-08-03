import time
import json
from pathlib import Path
from fastapi.testclient import TestClient

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db_api.main import app
client = TestClient(app)

TOKEN = "super-secret"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

print("==================================================")
print(" TEST 1: augment=False (Sadece 1 Kayıt Ekleme)")
print("==================================================")

req1 = {
    "soru": "Yapay zeka tabanlı sanal sunucu ve siber güvenlik hizmeti arıyoruz.",
    "cevap": "bilisim",
    "augment": False
}

print(f"Gönderiliyor (augment=False): {req1['soru']}")
try:
    res1 = client.post("/api/admin/add_qa", json=req1, headers=HEADERS)
    print(f"Status: {res1.status_code}")
    print(f"Response: {json.dumps(res1.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")

print("\n(Arkaplandaki indexlemenin bitmesi için 3 saniye bekleniyor...)\n")
time.sleep(3)


print("==================================================")
print(" TEST 2: augment=True (Varyasyon Üretme)")
print("==================================================")

req2 = {
    "soru": "Hastane sistemimiz için randevu ve reçete otomasyon yazılımı entegre etmek istiyoruz.",
    "cevap": "saglik",
    "augment": True
}

print(f"Gönderiliyor (augment=True): {req2['soru']}")
try:
    res2 = client.post("/api/admin/add_qa", json=req2, headers=HEADERS)
    print(f"Status: {res2.status_code}")
    data2 = res2.json()
    
    print("\n[+] Üretilen Varyasyonlar (Örtüşme < %50 Garantili):")
    for i, v in enumerate(data2.get("augmented_variations", [])):
        print(f"   {i+1}. {v}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n==================================================")
print(" TEST 3: Chatbot Doğrulama")
print("==================================================")
print("Yeni eklenen verilerin index'ten bulunabildiğini test ediyoruz...")

test_queries = [
    "Sanal sunucu siber güvenlik",
    "Reçete otomasyon sistemleri randevu"
]

for tq in test_queries:
    print(f"\nSoru: {tq}")
    try:
        c_res = client.post("/api/chat", json={"message": tq})
        if c_res.status_code == 200:
            js = c_res.json()
            intents = js.get("intents", {})
            print(f"  Bulunan Sektör/URL: {intents.get('url', 'Bulunamadı')}")
        else:
            print(f"  Chat API Error: {c_res.status_code} - {c_res.text}")
    except Exception as e:
        print(f"  Hata: {e}")

print("\nTEST TAMAMLANDI.")
