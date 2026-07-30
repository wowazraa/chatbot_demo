import urllib.request
import subprocess
import time
import urllib.error

# Start server
proc = subprocess.Popen(['uvicorn', 'db_api.main:app', '--host', '127.0.0.1', '--port', '8005'])
time.sleep(3)

try:
    # Valid Origin
    req = urllib.request.Request('http://127.0.0.1:8005/api/health')
    req.add_header('Origin', 'http://localhost:5000')
    with urllib.request.urlopen(req) as response:
        print('Valid Origin response code:', response.status)
        print('Valid Origin headers:', response.headers.get('Access-Control-Allow-Origin'))

    # Invalid Origin
    req2 = urllib.request.Request('http://127.0.0.1:8005/api/health')
    req2.add_header('Origin', 'http://evil.com')
    with urllib.request.urlopen(req2) as response:
        print('Invalid Origin response code:', response.status)
        print('Invalid Origin headers:', response.headers.get('Access-Control-Allow-Origin'))
except urllib.error.URLError as e:
    print('Error:', e)
finally:
    proc.terminate()

