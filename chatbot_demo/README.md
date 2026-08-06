# Chatbot Bilgi Merkezi — B2B Intent Router

Allintos sitesine gömülebilen B2B niyet yönlendirme servisi. Kullanıcı mesajını **5 sektöre** (sağlık, eğitim, bilişim, turizm, eğlence) yönlendirir veya belirsiz / OOD döner.

**Veri kaynağı (üretim):** Allintos PostgreSQL (`qa_embeddings`, `knowledge_documents`, oturum tabloları). Yerel `vector_index` / NPZ yalnızca **fallback**.

## Proje yapısı

```
chatbot_demo/
├── main.py                 # uvicorn giriş noktası
├── app/
│   ├── api/                # chat, health, conversations, admin_qa
│   ├── core/               # config, guardrails, intent contract
│   ├── db/                 # vector store, Allintos bağlantıları
│   ├── models/             # ORM
│   └── services/           # V2IntentPipeline, K0, session, embedder
├── static/
│   ├── chatbot_widget.js   # embed widget
│   ├── chatbot_widget.css
│   └── widget_test.html    # yerel demo (/)
├── scripts/                # indeks, seed, Allintos entegrasyon testleri
├── config/router_config.json
├── data/raw/
│   └── chatbot_dataset.json   # ham corpus (repoda)
├── Dockerfile
└── .env.example
```

**Repoda olmayan (gitignore, yerelde kalır):**

| Klasör / dosya | Amaç |
|----------------|------|
| `scratch/` | Geliştirme test scriptleri (`kurumsal_test_set.py` vb.) |
| `_final_dogrulama.py` | Ana regresyon seti (~165 vaka) |
| `reports/` | Test çıktıları |
| `data/processed/` | `embeddings.npz`, `index_meta.json` (build ile üretilir) |
| `static/widget_test_*.html` | (kaldırıldı — yalnızca `widget_test.html` yeterli) |

`db_api/` yalnızca eski komutlar için 2 satırlık shim (`main.py`, `seed_cli.py`).

## Hızlı başlangıç

```powershell
cd chatbot_demo
pip install -r ../requirements.txt
copy .env.example .env    # ALLINTOS_DB_URL, ALLINTOS_RETRIEVAL_MODE=primary vb.
uvicorn main:app --host 0.0.0.0 --port 8082
```

Tarayıcı: **http://127.0.0.1:8082/** (widget demo)

### Allintos birincil mod (önerilen)

`.env` içinde:

```env
ALLINTOS_RETRIEVAL_MODE=primary
ALLINTOS_K0_SOURCE=allintos
ALLINTOS_CHAT_DB=allintos
ALLINTOS_LOCAL_FALLBACK=true
ALLINTOS_DB_URL=postgresql+psycopg2://...@host:5433/allintos
ALLINTOS_SITE_URL=http://10.20.40.154:5000
```

Intent form URL'leri için (ilk kurulum veya site URL değişince):

```powershell
python -m scripts.seed_cli
```

### Yerel fallback kurulumu (Allintos yokken)

```powershell
python -m scripts.setup_local_db
python scripts/build_index.py
python scripts/seed_pgvector.py --truncate
```

## Pipeline özeti

1. **K0** — Kurumsal terimler (`turquality nedir` vb.) → `knowledge_documents` (Allintos) veya yerel JSON
2. **Session** — Takip sorularında `aktif_sektor` hafızası
3. **K1** — Chitchat, savunma reddi, kısaltma kuralları
4. **K2** — BGE-M3 + vektör arama (`qa_embeddings` primary; NPZ/pgvector fallback)
5. **Fallback** — Düşük skor → belirsiz / OOD; unresolved log

## Testler

Yerel scriptler (gitignore — clone sonrası ekibinizde mevcut olmalı):

```powershell
python _final_dogrulama.py
python scratch/kurumsal_test_set.py
```

Repodaki entegrasyon kontrolleri:

```powershell
python scripts/check_allintos_integration_status.py
python scripts/test_full_allintos_integration.py
python scripts/test_k0_allintos_source.py
python scripts/test_pipeline_primary_mode.py
python scripts/test_allintos_retrieval_manual.py
```

## Skor özeti (son doğrulama)

| Set | Skor |
|-----|------|
| `_final_dogrulama.py` | 142 / 165 (~86%) |
| `scratch/kurumsal_test_set.py` | 31 / 31 |
| `scripts/test_full_allintos_integration.py` | 4 / 4 |

## API

| Endpoint | Açıklama |
|----------|----------|
| `POST /api/chat` | Mesaj → cevap + `url` + `session_id` |
| `GET /api/messages` | Oturum geçmişi |
| `GET /api/health` | Sağlık kontrolü |
| `POST /api/admin/add_qa` | QA ekleme (Bearer `ADMIN_API_TOKEN`) |
| `/docs` | Swagger |

Widget embed:

```html
<script src="http://HOST:8082/static/chatbot_widget.js" data-language="tr"></script>
```

## Ortam değişkenleri

Tam liste: `.env.example`. Önemliler:

| Değişken | Açıklama |
|----------|----------|
| `ALLINTOS_RETRIEVAL_MODE` | `local` \| `primary` \| `shadow` |
| `ALLINTOS_K0_SOURCE` | `allintos` \| `local` |
| `ALLINTOS_CHAT_DB` | `allintos` \| `local` |
| `ALLINTOS_LOCAL_FALLBACK` | Allintos hata → yerel indeks |
| `ALLINTOS_DB_URL` | Allintos PostgreSQL |
| `ALLINTOS_SITE_URL` | Dijital olgunluk form kök URL |
| `DATABASE_URL` | Yerel Postgres (fallback / vector_index) |
| `ADMIN_API_TOKEN` | Admin API |

## Docker

```powershell
# Proje kökünden
docker build -f chatbot_demo/Dockerfile -t chatbot-demo .
docker run --rm -p 8082:8082 --env-file chatbot_demo/.env chatbot-demo
```

Stack compose dosyası backend ekibi tarafından sağlanacaktır.
