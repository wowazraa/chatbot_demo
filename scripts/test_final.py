import requests
import time
import subprocess
import json

def test_api():
    server = subprocess.Popen(["python", "-m", "uvicorn", "db_api.main:app", "--port", "8000"], 
                              cwd=r"c:\Users\KAAN EFE\chatbot_bsy\chatbot_demo")
    
    print("Waiting for server to start...")
    time.sleep(10)
    
    tests = [
        "Hastane randevu sistemi arıyoruz",
        "Eğitim için öğrenci otomasyonu lazım",
        "Otel ve check-in yazılımı gerekli",
        "Askeri haberleşme ve komuta kontrol altyapısı kurmak istiyoruz",
        "Savunma sanayi alanında siber güvenlik yatırımı",
        "NATO standartlarında kriptolu mesajlaşma"
    ]
    
    print("\n--- TEST RESULTS ---")
    for t in tests:
        try:
            resp = requests.post("http://localhost:8000/api/chat", json={
                "message": t,
                "session_id": 1,
                "user_identifier": "test-user"
            }).json()
            reply = resp.get("reply", "UNKNOWN")
            url = resp.get("url", "NONE")
            print(f"Query: '{t}'")
            print(f"Reply: {reply}")
            print(f"URL: {url}\n")
        except Exception as e:
            print(f"Query: '{t}' -> Error: {e}\n")
            
    server.terminate()

if __name__ == "__main__":
    test_api()
