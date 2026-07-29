# Chat API v2.2 — session_id akışı

## Uçlar
| | | |
|--|--|--|
| GET | `/api/health` | `{ "status": "ok" }` |
| POST | `/api/chat` | `reply`, `url`, `session_id` |
| GET | `/api/messages?session_id=` | `role`, `content` |

## session_id (önemli)
1. Environment: **Chatbot Chat API — Local 8001** (eski DB env kullanma)
2. Collection Variables’ta `session_id` başta **boş**
3. **2 POST chat** → ilk sefer `null`, cevap id’yi Collection’a yazar
4. **3 GET messages** → aynı id

Aynı oturuma ikinci mesaj: **2 POST chat**’i tekrar Send (artık `session_id` dolu).
Yeni sohbet: Collection Variables → `session_id` boşalt, tekrar POST.

## Kurulum
```powershell
cd chatbot_demo
uvicorn db_api.main:app --host 127.0.0.1 --port 8001
python -m db_api.seed_cli
```

Eski collection’ı sil → `postman_collection.json` + `postman_environment.json` yeniden import.
