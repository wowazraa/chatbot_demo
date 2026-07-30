import requests
import time
import subprocess

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
            intent = resp.get("metadata", {}).get("intent", "UNKNOWN")
            print(f"Query: '{t}'")
            print(f"Intent: {intent}\n")
        except Exception as e:
            print(f"Query: '{t}' -> Error: {e}\n")
            
    server.terminate()

if __name__ == "__main__":
    test_api()
