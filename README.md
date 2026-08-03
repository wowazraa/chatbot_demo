# OmniIntent / Allintos — B2B Niyet Yönlendirme (Intent Routing) Altyapısı

Bu doküman, Chatbot B2B Niyet Yönlendirme altyapısının **güncel mimarisini**, kurulum adımlarını ve doğrulanmış skorlarını tek bir kaynakta özetler.

## 1. Mimari Özeti (V2IntentPipeline)
Sistem, kullanıcının girdiği metni **5 temel B2B sektörel kategoriye** (sağlık, eğitim, bilişim, turizm, eğlence) veya "belirsiz" (fallback) statüsüne atamak için modern bir çok katmanlı yapı kullanır. Önceki mimaride bulunan `chatbot.py` kavram kargaşası tamamen temizlenmiş ve tüm karar mekanizması `V2IntentPipeline` çatısı altında toplanmıştır. (Savunma sektörü güvenlik gereği bilinçli olarak reddedilir).

- **Aşama 1 (Hafıza / Session State):** Kullanıcının önceki turda belirlenmiş geçerli bir `aktif_sektor`'ü varsa ve yeni girdi küçük bir takip sorusuysa (örn: "Fiyat alabilir miyim?"), sistem BGE-M3'ü pas geçerek doğrudan `HAFIZA` modunda önceki sektörü döndürür.
- **Aşama 2 (K1 Guardrails & Kural Motoru):** Hızlı reddetme (chit-chat, hava durumu vb.) ve **yasaklı kelime (savunma sanayi vs.)** kontrolleri Regex ile yapılır. Kesin sektör kısaltmaları tespit edilirse anında ilgili sektöre yönlendirilir.
- **Aşama 3 (K2 Vektör Veritabanı - BGE-M3):** K1'den geçen metinler BAAI/bge-m3 modeliyle vektörel (1024 boyutlu) embedding'e dönüştürülür. Yerel `embeddings.npz` indeksi üzerinden kosinüs benzerliği aranır.
- **Aşama 4 (Konsensüs & Fallback):** Top-K sonuçlarının skorları toplanarak en olası sektör seçilir. Skor `0.65` eşiğinin altındaysa sistem "belirsiz" (Fallback - FB) moduna düşer.
- **Aşama 5 (Session Memory Fallback & Trap Koruması):** OOD veya "belirsiz" sınırında kalan girdiler için, eğer `session_id` içerisinde daha önce doğrulanmış bir `aktif_sektor` varsa, sistem o bağlamı kullanarak OOD kararını sektöre zorlar. Aşırı genelleme hatalarını önlemek için `trap_keywords` kara listesiyle korunmaktadır.
- **Aşama 6 (Aktif Öğrenme Günlüğü / Active Learning):** Nihai olarak "belirsiz" (FB) kararı verilen sorgular `src/unresolved_logger.py` mekanizması tarafından otomatik olarak loglanır (`logs/unresolved_queries.json`).

## 2. Güncel Skor Tablosu (North Star Metriği)
Tüm mimari refactor adımları sonrasında sistemin performansı kayıpsız korunmuştur. Yalnızca hedeflenen sektörün doğru bulunup bulunmadığına bakan son başarı skoru: **148 / 165 (%89.7)**

- **TEMEL (19 Senaryo):** 18/19 (%94.7)
- **STRES (78 Senaryo):** 64/78 (%82.0)
- **ÇEKİM EKİ (26 Senaryo):** 26/26 (%100)
- **SELAMLAŞMA (26 Senaryo):** 24/26 (%92.3)
- **K1 REGEX/HAFIZA (16 Senaryo):** 16/16 (%100)

## 3. Proje Yapısı

```
chatbot_demo/
├── main.py                 # Uygulama giriş noktası
├── app/
│   ├── api/
│   │   ├── chat.py         # POST /api/chat
│   │   ├── health.py
│   │   ├── conversations.py
│   │   └── admin_qa.py
│   ├── core/
│   │   ├── config.py       # .env + router_config.json
│   │   ├── intent_contract.py
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
│   │   └── pipeline_service.py   # V2IntentPipeline orkestratörü
│   └── schemas.py
├── static/                 # Widget (chatbot_widget.js/css)
├── scripts/                # build_index, seed_pgvector, seed_cli, data_augmented, setup_local_db
├── data/                   # Ham + işlenmiş corpus
├── tests/
└── config/router_config.json
```

Katman ayrımı:
- **API** → HTTP uçları (`app/api/`)
- **Services** → iş mantığı (K1/K2, fallback, session)
- **DB** → PostgreSQL + pgvector
- **static/** → frontend widget
- **scripts/** → veri hazırlama

> `db_api/` ve `src/` yalnızca geriye dönük import shim'leri içerir (eski komutlar çalışmaya devam eder).

## 4. Çalıştırma Rehberi

### Sıfır Kurulum (İlk Çalıştırma)
Eğer projeyi yeni clone'ladıysanız, `embeddings.npz` indeksi repoda olmadığı için oluşturmanız şarttır:
```powershell
pip install -r requirements.txt
python scripts/build_index.py
```

### API Sunucusunu Başlatmak
```powershell
uvicorn main:app --host 127.0.0.1 --port 8082
```
(Eski komut `uvicorn db_api.main:app` hâlâ çalışır.)

- **Demo Widget:** `http://127.0.0.1:8082/` veya `static/widget_test.html`
- **Swagger:** `http://127.0.0.1:8082/docs`

### Regresyon Testlerini Çalıştırmak
Test senaryolarını doğrulamak için:
```powershell
python _final_dogrulama.py
python tests/run_cekim_eki_orijinal.py
```

## 5. Admin API ve Veritabanı Entegrasyonu (Beklemede)
**Endpoint:** `POST /api/admin/add_qa`

Bu uç, chatbot zekasına dokunmadan dinamik olarak yeni soru/cevap (`query`, `sector`, `augment`) eklenmesi amacıyla tasarlanmıştır. Bu mimarinin lokal indeks (JSON/NPZ) güncellemelerini de kapsaması amaçlanmaktadır; ancak **henüz uçtan uca test edilmemiştir**.

**Mevcut Durum:** Allintos ana PostgreSQL veritabanına (`qa_embeddings` tablosuna) bağlanacak olan asıl DB entegrasyonu (INSERT işlemi), veritabanında açılacak olan **5 intent ID'sinin Sinem'den beklenmesi** sebebiyle henüz kodlanmamıştır. İlgili `intent_id`'ler teslim alındığında `background_sync_allintos/admin_qa.py` kodu yazılacak ve tüm admin entegrasyonu (hem veritabanı hem lokal indeks güncellemeleri) baştan sona test edilecektir.
