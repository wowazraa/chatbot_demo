import requests
import time
import subprocess
import json

def test_api():
    server = subprocess.Popen(["python", "-m", "uvicorn", "db_api.main:app", "--port", "8000"], 
                              cwd=r"c:\Users\KAAN EFE\chatbot_bsy\chatbot_demo")
    
    print("Waiting for server to start...")
    time.sleep(10)
    
    try:
        resp = requests.post("http://localhost:8000/api/chat", json={
            "message": "Eğitim öğrenci sistemi",
            "session_id": 1,
            "user_identifier": "test-user"
        })
        print("RAW RESPONSE:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        
    server.terminate()

if __name__ == "__main__":
    test_api()
