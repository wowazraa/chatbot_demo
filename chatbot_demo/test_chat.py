import urllib.request
import json
import subprocess
import time

proc = subprocess.Popen(['python', '-m', 'uvicorn', 'db_api.main:app', '--host', '127.0.0.1', '--port', '8012'], cwd='C:\\Users\\AZRA\\OneDrive\\Desktop\\Chatbot_Bilgi_Merkezi_Projesi\\chatbot_demo')
time.sleep(5)

try:
    req = urllib.request.Request('http://127.0.0.1:8012/api/chat', method='POST')
    req.add_header('Content-Type', 'application/json')
    data = json.dumps({'message': 'okulumuz için LMS fiyatı alabilir miyiz?', 'session_id': None, 'user_identifier': 'test'})
    with urllib.request.urlopen(req, data=data.encode('utf-8')) as response:
        print("--- RESPONSE ---")
        print(response.read().decode('utf-8'))
        print("----------------")
finally:
    proc.terminate()
    proc.kill()
