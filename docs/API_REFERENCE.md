# Chatbot Bilgi Merkezi — API Referansı (doğrulanmış)

> **Kaynak:** `main.py` + `app/api/*.py` — **2026-08-04** tarihinde `uvicorn main:app --port 8082` üzerinde canlı isteklerle doğrulandı.  
> Canlı yanıt kayıtları: `scratch/api_doc_live_responses.json`

## Base URL

| Ortam | URL |
|-------|-----|
| Lokal (varsayılan) | `http://127.0.0.1:8082` |
| Widget test (alternatif) | `http://127.0.0.1:8001` |

Swagger UI: `{base_url}/docs`  
OpenAPI JSON: `{base_url}/openapi.json`

## Mount edilen router'lar

`main.py` içinde `app.include_router(..., prefix="/api")`:

| Router dosyası | Tag | Prefix (router içi) |
|----------------|-----|---------------------|
| `app/api/health.py` | health | — |
| `app/api/chat.py` | chat | — |
| `app/api/conversations.py` | messages | — |
| `app/api/admin_qa.py` | admin | `/admin` |

---

## Endpoint özeti

| Method | Path | Auth | Açıklama |
|--------|------|------|----------|
| GET | `/api/health` | Hayır | DB bağlantı kontrolü |
| POST | `/api/chat` | Hayır | Kullanıcı mesajı → bot yanıtı |
| GET | `/api/messages` | Hayır | Mesaj geçmişi (sayfalı) |
| GET | `/api/status` | Hayır | `/api/messages` ile **aynı handler** (alias) |
| GET | `/api/api/messages` | Hayır | Geriye dönük alias (çift `/api` prefix) |
| GET | `/api/api/status` | Hayır | Geriye dönük alias |
| POST | `/api/admin/add_qa` | **Evet** | Dataset + index'e yeni QA ekleme |
| GET | `/` | Hayır | Widget test HTML sayfası (JSON API değil) |

> **Önerilen path'ler:** `/api/messages`, `/api/status`. `/api/api/*` yalnızca geriye dönük uyumluluk içindir.

---

## 1. GET `/api/health`

**Auth:** Gerekmez

**Response 200** (gerçek):
```json
{
  "status": "ok"
}
```

**Response 503:** PostgreSQL erişilemezse `{"detail": "database unavailable: ..."}`

---

## 2. POST `/api/chat`

**Auth:** Gerekmez  
**Content-Type:** `application/json`

### Request body — `ChatTurnRequest`

| Alan | Tip | Zorunlu | Varsayılan | Açıklama |
|------|-----|---------|------------|----------|
| `message` | string | * | — | Kullanıcı mesajı (`query` ile alternatif) |
| `query` | string | * | — | `message` ile alternatif |
| `user_identifier` | string | Hayır | `"web-user"` | Oturum sahibi kimliği |
| `session_id` | integer | Hayır | `null` | Mevcut DB session id (devam eden sohbet) |
| `external_session_id` | string | Hayır | `null` | Harici sistem session id (widget) |
| `lang` | string | Hayır | `null` | Bot yanıt dili: `tr` veya `en` (widget her istekte gönderir) |

\* `message` veya `query` en az biri dolu olmalı (trim sonrası).

### `session_id` ve hafıza akışı

Pipeline, oturum bazlı `aktif_sektor` hafızasını tutarlı bir anahtarla kullanır (`api-{db_session_id}`):

| Tur | İstek | Yanıt |
|-----|-------|-------|
| **Turn 1** | `session_id: null` | Yanıtta yeni `session_id` (örn. `74`) döner; sektör belirlenir |
| **Turn 2+** | Aynı `session_id` (örn. `74`) | Önceki sektör korunur; takip soruları (`fiyat alabilir miyim?`, `can I get a price estimate?`) OOD yerine aynı sektöre yönlendirilir |

Widget, Turn 1 yanıtındaki `session_id`'yi `sessionStorage` (`ag_chatbot_session_id`) içinde saklar ve sonraki isteklerde geri gönderir.

### Örnek istek — Türkçe (gerçek)
```json
{
  "message": "LMS entegrasyonu ve uzaktan egitim altyapisi ariyoruz",
  "external_session_id": "api-doc-test-1042",
  "user_identifier": "api-doc-tester"
}
```

### Örnek yanıt 200 — Türkçe (gerçek — 2026-08-04)
```json
{
  "reply": "Talebinizi eğitim sektörüyle ilişkilendirdim. İlgili forma buradan ulaşabilirsiniz: https://example.com/forms/education",
  "url": "https://example.com/forms/education",
  "session_id": 58
}
```

### Örnek istek — İngilizce + hafıza (doğrulanmış — 2026-08-04)

**Turn 1:**
```json
{
  "message": "we need a hotel booking system",
  "session_id": null,
  "lang": "en",
  "user_identifier": "api-doc-tester"
}
```

**Turn 1 yanıtı:**
```json
{
  "reply": "I've matched your request to the tourism sector. You can proceed here: https://example.com/forms/tourism",
  "url": "https://example.com/forms/tourism",
  "session_id": 74
}
```

**Turn 2** (aynı `session_id`, takip sorusu):
```json
{
  "message": "can I get a price estimate?",
  "session_id": 74,
  "lang": "en",
  "user_identifier": "api-doc-tester"
}
```

**Turn 2 yanıtı:**
```json
{
  "reply": "I've matched your request to the tourism sector. You can proceed here: https://example.com/forms/tourism",
  "url": "https://example.com/forms/tourism",
  "session_id": 74
}
```

> `lang` gönderilmezse hafıza çalışsa bile kısa İngilizce takip sorularında bot cevabı Türkçe'ye düşebilir; widget her istekte `lang` gönderir.

### Hata yanıtları (gerçek)

**400** — mesaj boş:
```json
{
  "detail": "message or query is required"
}
```

**503** — router/model yüklenemezse:
```json
{
  "detail": "router unavailable: ..."
}
```

> **Not:** Yanıtta artık `sector`, `layer_hit`, `confidence` alanları **yok**. Sadece `reply`, `url`, `session_id` döner.

---

## 3. GET `/api/messages` (ve alias'lar)

**Auth:** Gerekmez

Aynı handler: `/api/messages`, `/api/status`, `/api/api/messages`, `/api/api/status`

### Query parametreleri

| Param | Tip | Zorunlu | Varsayılan | Açıklama |
|-------|-----|---------|------------|----------|
| `conversation_id` | integer | Hayır | — | Belirli konuşma |
| `session_id` | string | Hayır | — | `sessions.id` (sayısal string) |
| `limit` | integer | Hayır | 50 | 1–500 |
| `offset` | integer | Hayır | 0 | Sayfalama |

### Örnek: tüm mesajlar (gerçek yanıt — kısaltılmış)
```
GET /api/messages?limit=2&offset=0
```
```json
{
  "items": [
    {
      "role": "user",
      "content": "LMS entegrasyonu ve uzaktan eğitim altyapısı arıyoruz"
    },
    {
      "role": "bot",
      "content": "Talebinizi eğitim sektörüyle ilişkilendirdim. İlgili forma buradan ulaşabilirsiniz: https://example.com/forms/education"
    }
  ],
  "total": 188,
  "limit": 2,
  "offset": 0
}
```

### Örnek: session filtresi (gerçek)
```
GET /api/messages?session_id=58&limit=5
```
```json
{
  "items": [
    {
      "role": "user",
      "content": "LMS entegrasyonu ve uzaktan egitim altyapisi ariyoruz"
    },
    {
      "role": "bot",
      "content": "Talebinizi eğitim sektörüyle ilişkilendirdim. İlgili forma buradan ulaşabilirsiniz: https://example.com/forms/education"
    }
  ],
  "total": 2,
  "limit": 5,
  "offset": 0
}
```

**Response item şeması — `ChatMessageOut`:**

| Alan | Tip |
|------|-----|
| `role` | `"user"` \| `"bot"` |
| `content` | string |

---

## 4. POST `/api/admin/add_qa`

**Auth:** Gerekli — `Authorization: Bearer <admin-token>`

Token: `.env` içindeki `ADMIN_API_TOKEN` (dokümanda gerçek değer yazılmaz).

### Request body — `AddQaRequest`

| Alan | Tip | Zorunlu | Varsayılan | Açıklama |
|------|-----|---------|------------|----------|
| `query` | string | Evet | — | Soru metni |
| `answer` | string | Evet | — | Cevap metni |
| `sector` | string | Evet | — | `turizm`, `saglik`, `egitim`, `bilisim`, `eglence` |
| `augment` | boolean | Hayır | `false` | `true` ise 3 varyasyon daha üretir |

### Örnek istek
```json
{
  "query": "Otel rezervasyon sistemi entegrasyonu istiyoruz",
  "answer": "Turizm ekibimiz sizinle iletisime gececek.",
  "sector": "turizm",
  "augment": false
}
```

**Header:**
```
Authorization: Bearer <admin-token>
Content-Type: application/json
```

### Örnek yanıt 200 (gerçek — doğrulama testi)
```json
{
  "status": "success",
  "message": "1 kayıt eklendi, index arka planda güncelleniyor.",
  "original": "API-DOC-VERIFY-2026 silinebilir",
  "augmented_variations": []
}
```

### Örnek yanıt 401 (gerçek — token yok)
```json
{
  "detail": "Unauthorized"
}
```

> **Uyarı:** Bu endpoint lokal JSON dataset'e yazar ve arka planda index sync tetikler. Test ortamında dikkatli kullanın.

---

## Eski Postman koleksiyonu ile karşılaştırma

Kaynak: `Allintos/Allintos/B2B_Intent_Router.postman_collection.json`

| Konu | Eski koleksiyon | Güncel API (doğrulandı) |
|------|-----------------|-------------------------|
| Base URL | `http://127.0.0.1:8080`, `ai_chatbot_api:8080` | `http://127.0.0.1:8082` (veya 8001) |
| `GET /api/health` | Var | Var — aynı `{status: ok}` |
| `POST /api/chat` | Var | Var |
| Chat response alanları | `reply`, `url`, `session_id`, **`sector`**, **`layer_hit`**, **`confidence`** | Yalnızca **`reply`**, **`url`**, **`session_id`** |
| `GET /api/messages` | **Yok** | **Var** (önerilen) |
| `GET /api/status` | Var | Var — `/api/messages` ile aynı |
| `POST /api/admin/add_qa` | **Yok** | **Var** — auth gerekli |
| Chat request | `message`, `external_session_id`, `user_identifier` | Aynı + opsiyonel `query`, `session_id`, **`lang`** |
| Validation error | 422 örneği (`user_identifier` required) | Boş body → **400** `message or query is required` (`user_identifier` varsayılan `"web-user"`) |

---

## Hızlı test (curl)

```bash
# Health
curl -s http://127.0.0.1:8082/api/health

# Chat
curl -s -X POST http://127.0.0.1:8082/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Otel rezervasyon yazilimi ariyoruz","user_identifier":"test-user"}'

# Messages
curl -s "http://127.0.0.1:8082/api/messages?limit=5"

# Admin (token placeholder)
curl -s -X POST http://127.0.0.1:8082/api/admin/add_qa \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"query":"test","answer":"test","sector":"turizm","augment":false}'
```

---

## Postman

Güncel koleksiyon: [`postman/Chatbot_API.postman_collection.json`](../postman/Chatbot_API.postman_collection.json)  
Ortam değişkenleri: [`postman/Chatbot_API.postman_environment.json`](../postman/Chatbot_API.postman_environment.json)

| Değişken | Açıklama |
|----------|----------|
| `base_url` | `http://127.0.0.1:8082` |
| `admin_token` | `.env` → `ADMIN_API_TOKEN` (Postman'de elle set edin) |
