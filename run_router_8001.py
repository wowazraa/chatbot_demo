"""Bootstrap: chatbot_demo dizinine chdir edip B2B Intent Router'ı 8001'de başlatır.
launch.json'daki cwd desteksizliğini aşmak için — hangi dizinden çalıştırılırsa
çalıştırılsın kendi konumuna göre sys.path/cwd ayarlar.
"""

import os
import sys
import uvicorn

_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
sys.path.insert(0, _HERE)

from db_api.main import app

if __name__ == "__main__":
    uvicorn.run("db_api.main:app", host="127.0.0.1", port=8001, reload=False)
