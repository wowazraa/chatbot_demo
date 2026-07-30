# OmniIntent / Allintos — Çalıştırma Rehberi

Bu dosya **demo arayüzü** ve **API endpoint**lerini nasıl ayağa kaldıracağını, nasıl test edeceğini anlatır.  
(Teknik mimari detayı için: `docs/ARCHITECTURE_SPEC.md`)

---

## İki ayrı sunucu var — karıştırma

| Ne | Ne işe yarar | Adres | Komut |
|----|--------------|-------|--------|
| **Demo (UI)** | Mentörün tarayıcıdan denediği chatbot ekranı | http://127.0.0.1:8080 | `python demo/server.py` |
| **Chat API** | Postman / curl / Swagger ile endpoint testi | http://127.0.0.1:8001 | `uvicorn db_api.main:app --host 127.0.0.1 --port 8001` |

- Demo **veritabanı olmadan** çalışabilir (NPZ + BGE).
- Chat API **yerel Postgres** ister (`.env` → `localhost:5432/chatbot_db`).

---

## 0) Her seferinde önce buraya gir

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
```

---

## 1) Demo sunucusunu çalıştır / yeniden başlat

### İlk kez veya yeniden başlatma

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
python demo/server.py
```

Tarayıcı: **http://127.0.0.1:8080**

### Port 8080 meşgulse (eski sunucu hâlâ açık)

```powershell
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
python demo/server.py
```

### Durdurmak

Terminalde `Ctrl + C`

### Demo ne sunar?

| Yol | Açıklama |
|-----|----------|
| `GET /` | Chat arayüzü (HTML) |
| `GET /api/status` | Corpus boyutu, BGE durumu, eşik vb. |
| `POST /api/chat` | Mesaj at → sektör / skor / Top-3 inspector |

Örnek (PowerShell):

```powershell
curl http://127.0.0.1:8080/api/status
curl -X POST http://127.0.0.1:8080/api/chat -H "Content-Type: application/json" -d "{\"message\":\"Hastane randevusu\",\"session\":\"\"}"
```

---

## 2) Chat API (endpoint’ler) — Postman / Swagger

### Postgres hazır olsun

`.env` içinde (varsayılan):

```text
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_db
```

Şifren farklıysa burayı kendi bilgine göre düzelt.

İlk kurulum (DB + tablolar):

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
python -m db_api.setup_local_db
python -m db_api.seed_cli
```

### API’yi başlat

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
uvicorn db_api.main:app --host 127.0.0.1 --port 8001
```

- Swagger (kolay test): **http://127.0.0.1:8001/docs**
- Port meşgulse:

```powershell
Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Endpoint listesi

| Method | Yol | Ne yapar |
|--------|-----|----------|
| `GET` | `/api/health` | API ayakta mı? |
| `POST` | `/api/chat` | Mesaj → `reply`, `url`, `session_id` |
| `GET` | `/api/messages?session_id=...` | O oturumun mesaj geçmişi |

### curl ile hızlı test

```powershell
# 1) Sağlık kontrolü
curl http://127.0.0.1:8001/api/health

# 2) Chat (ilk mesaj — session_id null)
curl -X POST http://127.0.0.1:8001/api/chat `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"Hastane randevusu almak istiyorum\",\"session_id\":null}"

# 3) Geçmiş (cevaptaki session_id ile)
curl "http://127.0.0.1:8001/api/messages?session_id=BURAYA_SESSION_ID"
```

### Postman

1. `db_api/postman_collection.json` import et  
2. `db_api/postman_environment.json` import et (`base_url` = `http://127.0.0.1:8001`)  
3. Sıra: **health → chat → messages**  
4. Detay: `db_api/POSTMAN.md`

---

## 3) Hangisini ne zaman kullan?

| Amaç | Kullan |
|------|--------|
| Mentör demosu, Top-3, sektör denemesi | **Demo 8080** |
| API / Postman / Swagger, reply+url | **API 8001** |
| Sadece motor (UI yok) | `python -c` ile `Chatbot().sor(...)` (geliştirici) |

İkisi aynı anda açık olabilir (farklı portlar).

---

## 4) Sık görülen hatalar

| Hata | Anlamı | Ne yap |
|------|--------|--------|
| `ERR_EMPTY_RESPONSE` / port kullanımda | Eski sunucu kapanmamış | Yukarıdaki `Stop-Process` komutu |
| `database unavailable` / connection refused | Postgres kapalı veya yanlış port | Yerel Postgres 5432 açık mı bak; `.env` kontrol et |
| İlk mesaj çok yavaş | Model soğuk açılış | 1–2 sorgu sonra hızlanır (normal) |
| `ModuleNotFoundError` | Yanlış klasör | Mutlaka `chatbot_demo` içinde çalıştır |

---

## 5) Manuel demo test (kısa hatırlatma)

Tarayıcıda http://127.0.0.1:8080 açıp örnekler:

- Net: `Hastane randevusu`, `Müze kart fiyatı`, `Askeri lise sınav`
- Sohbet: `Merhaba`, `Teşekkür ederim`
- Konu dışı (belirsiz olmalı): `Bugün hava güzel`, `Pizza sipariş`

---

## 6) Testler (opsiyonel)

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
python -m pytest tests/test_faz5_generalization.py tests/test_rerank_gate_demo.py -q
```

---

## Özet — kopyala-yapıştır

**Demo yeniden başlat:**

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
python demo/server.py
```

**API yeniden başlat:**

```powershell
cd C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo
Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
uvicorn db_api.main:app --host 127.0.0.1 --port 8001
```

---

## 7) Model Hakkında (BGE-M3)

Projede kullanılan **BAAI/bge-m3** modeli, Hugging Face Hub üzerinden standart ön eğitimli (pretrained) bir model olarak ilk çalıştırmada otomatik olarak indirilir ve lokal Hugging Face önbelleğinde (`~/.cache/huggingface` altında) saklanır. Model ağırlık dosyaları git repo'suna dahil edilmemiş olup `.gitignore` ile dışarıda bırakılmıştır.

