# OmniIntent / Allintos — B2B Niyet Yönlendirme (Intent Routing) Altyapısı

Bu doküman, Chatbot B2B Niyet Yönlendirme altyapısının **güncel mimarisini**, kurulum adımlarını ve doğrulanmış skorlarını tek bir kaynakta özetler.

## 1. Mimari Özeti (V2IntentPipeline)
Sistem, kullanıcının girdiği metni **5 temel B2B sektörel kategoriye** (sağlık, eğitim, bilişim, turizm, eğlence) veya "belirsiz" (fallback) statüsüne atamak için modern bir çok katmanlı yapı kullanır. Önceki mimaride bulunan `chatbot.py` kavram kargaşası tamamen temizlenmiş ve tüm karar mekanizması `V2IntentPipeline` çatısı altında toplanmıştır. (Savunma sektörü güvenlik gereği bilinçli olarak reddedilir).

- **Aşama 1 (Hafıza / Session State):** Kullanıcının önceki turda belirlenmiş geçerli bir `aktif_sektor`'ü varsa ve yeni girdi küçük bir takip sorusuysa (örn: "Fiyat alabilir miyim?" / "can I get a price estimate?"), sistem BGE-M3'ü pas geçerek doğrudan `HAFIZA` / SessionMem modunda önceki sektörü döndürür.
  - **API sid_key tutarlılığı (fix):** `POST /api/chat` pipeline'dan **önce** `ensure_chat_session()` ile DB oturumu oluşturur veya getirir. Pipeline anahtarı her turda tutarlıdır: `api-{db_session_id}` (widget yolu). Eski davranışta Turn 1 `api-web-user`, Turn 2 `api-{id}` kullanılıyordu → `aktif_sektor` kayboluyordu; takip soruları OOD'a düşüyordu. Örnek: `hastane randevu sistemi arıyoruz` → `fiyat alabilir miyim?` artık sağlık sektörünü korur.
- **Aşama 2 (K1 Guardrails & Kural Motoru):** Hızlı reddetme (chit-chat, hava durumu vb.) ve **yasaklı kelime (savunma sanayi vs.)** kontrolleri Regex ile yapılır. Kesin sektör kısaltmaları tespit edilirse anında ilgili sektöre yönlendirilir.
- **Aşama 3 (K2 Vektör Veritabanı - BGE-M3):** K1'den geçen metinler BAAI/bge-m3 modeliyle vektörel (1024 boyutlu) embedding'e dönüştürülür. Yerel `embeddings.npz` indeksi üzerinden kosinüs benzerliği aranır.
- **Aşama 4 (Konsensüs & Fallback):** Top-K sonuçlarının skorları toplanarak en olası sektör seçilir. Skor `0.65` eşiğinin altındaysa sistem "belirsiz" (Fallback - FB) moduna düşer.
- **Aşama 5 (Session Memory Fallback & Trap Koruması):** OOD veya "belirsiz" sınırında kalan girdiler için, eğer `session_id` içerisinde daha önce doğrulanmış bir `aktif_sektor` varsa, sistem o bağlamı kullanarak OOD kararını sektöre zorlar. Aşırı genelleme hatalarını önlemek için `trap_keywords` kara listesiyle korunmaktadır.
- **Aşama 6 (Aktif Öğrenme Günlüğü / Active Learning):** Nihai olarak "belirsiz" (FB) kararı verilen sorgular `app/services/unresolved_logger.py` mekanizması tarafından otomatik olarak loglanır (`logs/unresolved_queries.json`).

## 2. Güncel Skor Tablosu (North Star Metriği)
Son regresyon koşusu (`_final_dogrulama.py`): **146 / 165 (~88.5%)**

> Referans skor; dataset veya model küçük varyasyonlarıyla **~145–148** aralığında değişebilir.

- **TEMEL (19 Senaryo):** 18/19
- **STRES (78 Senaryo):** 64/78
- **ÇEKİM EKİ (26 Senaryo):** 25/26
- **SELAMLAŞMA (26 Senaryo):** 23/26
- **K1 REGEX/HAFIZA (16 Senaryo):** 16/16

## 3. Proje Yapısı

```
chatbot_demo/
├── main.py                 # Uygulama giriş noktası
├── app/
│   ├── api/
│   │   ├── chat.py         # POST /api/chat
│   │   ├── health.py
│   │   ├── conversations.py
│   │   └── admin_qa.py     # POST /api/admin/add_qa
│   ├── core/
│   │   ├── config.py       # .env + router_config.json
│   │   ├── intent_contract.py
│   │   ├── intent_mapping.py   # resolve_intent, source_id, index meta
│   │   ├── k1_guardrails.py
│   │   └── chitchat_rules.py
│   ├── db/
│   │   ├── database.py     # SQLAlchemy engine + ORM
│   │   ├── vector_store.py # pgvector arama
│   │   └── ...
│   ├── models/
│   │   └── tables.py       # ORM tabloları
│   ├── services/
│   │   ├── keyword_service.py    # K1 / chitchat eşleşmesi
│   │   ├── similarity_service.py # BGE-M3 + vektör arama
│   │   ├── fallback_service.py   # OOD / belirsiz yanıtlar
│   │   ├── session_service.py    # Oturum hafızası + DB persist
│   │   ├── pipeline_service.py   # V2IntentPipeline orkestratörü
│   │   ├── index_sync.py         # Incremental NPZ + pgvector (+ Allintos)
│   │   ├── dataset_ids.py        # max_id: raw + augmented + pg
│   │   └── embedder.py           # BGE-M3 encode
│   └── schemas.py
├── static/                 # Widget (chatbot_widget.js/css)
├── scripts/                # build_index, seed_pgvector, setup_local_db, …
├── data/                   # Ham + işlenmiş corpus
├── tests/
└── config/router_config.json
```

Katman ayrımı:
- **API** → HTTP uçları (`app/api/`)
- **Services** → iş mantığı (K1/K2, fallback, session, index sync)
- **DB** → PostgreSQL + pgvector
- **static/** → frontend widget
- **scripts/** → veri hazırlama

> `db_api/` ve `src/` yalnızca geriye dönük import shim'leri içerir (eski komutlar çalışmaya devam eder).

## 4. Çalıştırma Rehberi

### Sıfır Kurulum (İlk Çalıştırma)
Eğer projeyi yeni clone'ladıysanız, `embeddings.npz` indeksi repoda olmadığı için oluşturmanız şarttır:
```powershell
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL ve token'ları düzenleyin
python -m scripts.setup_local_db   # opsiyonel: yerel chatbot_db
python scripts/build_index.py
python scripts/seed_pgvector.py --truncate   # Postgres vector_index
```

### API Sunucusunu Başlatmak
```powershell
uvicorn main:app --host 127.0.0.1 --port 8082
```
(Eski komut `uvicorn db_api.main:app` hâlâ çalışır.)

Arkadaşının sitesinde widget göstermek için aynı makineden ağ erişimi:
```powershell
uvicorn main:app --host 0.0.0.0 --port 8082
```

- **Demo Widget:** `http://127.0.0.1:8082/` veya `static/widget_test.html`
- **Widget i18n test:** `widget_test_tr.html`, `widget_test_en.html`, `widget_test_lang_switch.html`
- **Widget kalıcılık test (Faz A):** `widget_persist_test_a.html`, `widget_persist_test_b.html`, `widget_persist_test_en.html`
- **Swagger:** `http://127.0.0.1:8082/docs`

### Regresyon Testlerini Çalıştırmak
```powershell
python _final_dogrulama.py
python tests/run_cekim_eki_orijinal.py
```

## 5. Admin API ve İndeks Senkronizasyonu

**Endpoint:** `POST /api/admin/add_qa`  
**Kimlik doğrulama:** `Authorization: Bearer <ADMIN_API_TOKEN>`

Admin panelden veya API ile eklenen her soru/cevap çifti:

1. `data/raw/chatbot_dataset.json` ve `data/processed/chatbot_dataset_augmented.json` dosyalarına yazılır.
2. Arka planda **`sync_new_qa_records()`** (`app/services/index_sync.py`) çalışır — **incremental** güncelleme:
   - BGE-M3 ile encode (tek sefer)
   - `embeddings.npz` + `index_meta.json` append (atomik yazım)
   - Postgres `vector_index` upsert (pgvector)
   - Opsiyonel Allintos `qa_embeddings` insert

**ID collision guard:** `source_id` zaten `index_meta.json`'da varsa işlem **`SourceIdCollisionError`** ile durur; sessiz overwrite veya duplicate append yapılmaz.

**Yeni kayıt ID'si:** `dataset_ids.compute_next_record_id()` — raw JSON, augmented JSON ve Postgres `vector_index.source_id` içindeki en büyük sayısal ID'nin bir fazlası.

### Incremental vs tam rebuild

| Senaryo | Yöntem |
|---|---|
| Admin'den tek/ birkaç QA ekleme | Otomatik incremental (`sync_new_qa_records`) |
| Toplu silme, corpus değişikliği, model değişimi | Manuel tam rebuild |

Tam rebuild adımları:
```powershell
python scripts/build_index.py
python scripts/seed_pgvector.py --truncate
```

### Allintos DB entegrasyonu

Allintos ana veritabanına (`qa_embeddings`) yazma **`index_sync._sync_allintos()`** üzerinden yapılır:

- `ALLINTOS_DB_ENABLED=true` → insert aktif
- `ALLINTOS_DB_URL` → PostgreSQL bağlantısı (**veritabanı adı: `allintos`**, örn. `postgresql+psycopg2://user:pass@host:5433/allintos`)
- Sektör → intent eşlemesi **`ALLINTOS_INTENT_ID_MAP`** (`app/core/intent_mapping.py`) içinde tanımlı

İzole test (admin endpoint / JSON dosyalarına dokunmadan):
```powershell
python scripts/test_allintos_db_isolated.py write
python scripts/test_allintos_db_isolated.py cleanup
```

## 6. Widget i18n (TR / EN — arayüz metinleri)

`static/chatbot_widget.js` **widget arayüzü** dilini otomatik seçer:

1. `<script src="…/chatbot_widget.js" data-language="tr">` — script tag attribute
2. `<html lang="en">` — sayfa dili (`document.documentElement.lang`)

İkisi çelişirse **sayfa dili (`html lang`)** önceliklidir.

Test sayfaları:
- `static/widget_test_tr.html` — Türkçe
- `static/widget_test_en.html` — İngilizce
- `static/widget_test_lang_switch.html` — canlı dil değiştirme

Harici siteye embed:
```html
<script src="http://SUNUCU_IP:8082/static/chatbot_widget.js" data-language="tr"></script>
```
Widget, API adresini script'in geldiği origin'den türetir (`/api/chat`).

### 6.1 Bot cevabı dili (`lang` — API katmanı)

Widget i18n yalnızca buton/placeholder gibi **UI metinlerini** değiştirir. Bot yanıtının dili `POST /api/chat` isteğindeki **`lang`** alanı ile belirlenir (`tr` / `en`):

| Katman | Dosya | Rol |
|--------|-------|-----|
| İstek şeması | `app/schemas.py` → `ChatTurnRequest.lang` | Opsiyonel; widget her istekte gönderir |
| Pipeline | `app/api/chat.py` → `force_lang` | Sektör tespiti sırasında dil ipucu |
| HTTP yanıt | `app/services/fallback_service.py` → `build_chat_reply(..., lang=)` | SUCCESS / UNCERTAIN / OOD şablonları TR ve EN |

Örnek (İngilizce bot cevabı):
```json
POST /api/chat
{ "message": "we need a hotel booking system", "session_id": null, "lang": "en" }
→ "I've matched your request to the tourism sector. You can proceed here: …"
```

Takip sorusu + hafıza + İngilizce birlikte: Turn 1'de sektör belirlenir, Turn 2'de aynı `session_id` ve `lang: "en"` ile `"can I get a price estimate?"` → sektör korunur, cevap İngilizce gelir.

### 6.2 Widget oturum ve mesaj kalıcılığı (Faz A)

`static/chatbot_widget.js` tarayıcı `sessionStorage` kullanır:

| Anahtar | İçerik |
|---------|--------|
| `ag_chatbot_session_id` | API'den dönen `session_id` (DB oturumu) |
| `ag_chatbot_state` | Mesaj geçmişi, son aktivite zamanı, dil |

- **20 dakika inaktivite:** `INACTIVITY_MS = 20 * 60 * 1000` — süre aşılırsa oturum ve geçmiş temizlenir.
- **Sayfa geçişi:** Aynı sekme/origin içinde sayfa yenilense veya başka sayfaya gidilse geçmiş korunur (`restoreFromStorage`).
- **API akışı:** Turn 1 `session_id: null` → yanıttaki id saklanır; sonraki turlarda aynı id gönderilir (sid_key fix ile pipeline hafızası da tutarlı kalır).

Test sayfaları: `static/widget_persist_test_a.html`, `widget_persist_test_b.html`, `widget_persist_test_en.html`

## 7. Ortam Değişkenleri (`.env`)

`.env.example` dosyasını kopyalayın. Önemli değişkenler:

| Değişken | Açıklama |
|---|---|
| `DATABASE_URL` | Yerel Postgres (`chatbot_db`) — V2 `vector_index`, oturum tabloları |
| `POSTGRES_DB` | `setup_local_db.py` için DB adı (varsayılan: `chatbot_db`) |
| `ADMIN_DATABASE_URL` | `setup_local_db.py` admin bağlantısı |
| `ADMIN_API_TOKEN` | `POST /api/admin/add_qa` Bearer token |
| `ALLINTOS_DB_ENABLED` | `true` / `false` — Allintos `qa_embeddings` sync |
| `ALLINTOS_DB_URL` | Allintos DB (**`allintos`**) bağlantı URL'si |

Gerçek şifre ve token'ları repoya commit etmeyin; yalnızca `.env.example` placeholder değerleri kullanın.
