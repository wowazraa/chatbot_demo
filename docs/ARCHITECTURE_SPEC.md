# Intent Router — Architecture Specification

Bu belge, Chatbot Bilgi Merkezi Intent Router’ının **mevcut (V1)** ve **hedef (V2)** mimarisini, dış JSON sözleşmesini ve adaptör katmanını tanımlar.

İlgili kod:
- Sözleşme / adaptör: `chatbot_demo/src/intent_router_contract.py`
- İç motor yanıtı: `chatbot_demo/src/chatbot.py` → `ChatbotResponse`
- API köprüsü: `chatbot_demo/db_api/routers/chat.py`
- Demo çıktı: `chatbot_demo/scripts/demo_intent_router_json.py`

Kalıcı Cursor kuralları: proje kökü `.cursorrules`.

---

## 1. Dış JSON sözleşmesi (Core Contract)

Sistem, dış dünyaya (API, UI `intent_router` alanı, persist) şu formatı döndürmelidir:

```json
{
  "query": "<kullanıcı_sorgusu>",
  "intent": {
    "sector": "<health | tourism | defense | education | ood>",
    "sub_intent": "<spesifik_aksiyon_etiketi>",
    "confidence_score": 0.85
  },
  "status": "<SUCCESS | UNCERTAIN | OOD>",
  "latency_ms": 112
}
```

| Alan | Açıklama |
|------|----------|
| `query` | Ham kullanıcı girdisi |
| `intent.sector` | İngilizce sektör kodu; kapsam dışıysa `ood` |
| `intent.sub_intent` | Noktalı aksiyon etiketi (örn. `health.appointment`) |
| `intent.confidence_score` | BGE (V1) veya reranker (V2) güven skoru |
| `status` | Karar durumu — aşağıya bakın |
| `latency_ms` | Uçtan uca süre (ms) |

### Status kuralları

| Status | Koşul |
|--------|--------|
| `SUCCESS` | Güven ≥ `MIN_BGE` (0.80) ve net sektör kararı (K1 / K2) veya session `HAFIZA` |
| `UNCERTAIN` | Fallback (`FB`) tetiklendi; skor eşiğe yakın veya margin çatışması var |
| `OOD` | Tamamen kapsam dışı / anlamlı sinyal yok |

**Kural:** False positive’e karşı `MIN_BGE=0.80` düşürülmez. Belirsizlikte `UNCERTAIN` veya `OOD` tercih edilir.

---

## 2. Adaptör katmanı (backward compatibility)

### Neden adaptör?

İç motor Türkçe alanlar ve legacy UI sözleşmesi kullanır:

- `sektor` (TR: `sağlık` / `turizm` / `savunma` / `eğitim` / `belirsiz`)
- `mod` (`K1` | `K2` | `HAFIZA` | `FB`)
- `skor`, `yontem`, `girdi`, …

Stres / crucible testleri ve Streamlit UI bu alanlara bağlıdır. Bu yüzden `ChatbotResponse` **yeniden adlandırılmaz**; dış spec `to_intent_router()` üzerinden üretilir.

```
Kullanıcı sorgusu
       │
       ▼
┌──────────────────┐
│  Chatbot.sor()   │  ← V1 motor (K1 → BGE → HAFIZA → FB)
└────────┬─────────┘
         │ ChatbotResponse (legacy alanlar korunur)
         ▼
┌──────────────────────────────┐
│ intent_router_contract.py    │
│  map_sector / map_sub_intent │
│  map_status / to_intent_…    │
└────────┬─────────────────────┘
         │ Spec JSON
         ▼
   API / UI / DB persist
```

### Geçici `sub_intent` mapper (V1)

Reranker ve pgvector henüz aktif değilken `sub_intent`:

1. İsteğe bağlı DB seed kodundan türetilir (`health_appointment` → `health.appointment`)
2. Yoksa sorgu anahtar kelimelerinden (örn. “randevu” → `health.appointment`)
3. Yoksa sektör varsayılanı (`health.general`, …); OOD için `ood.none`

V2’de bu mapper, aday intent’lerin rerank sonucuna bırakılacaktır.

---

## 3. Mevcut durum — V1 Pipeline

```
User Query
  → normalize / rewrite
  → K1 (kurumsal kısaltma sözlüğü; skor=1.0)
  → BGE-M3 hybrid search (yerel NPZ / bellek indeksi)
  → skor ≥ 0.80 + sektör margin? → K2 SUCCESS
  → skor ≥ 0.80 ama sektörler yakın? → FB UNCERTAIN
  → jenerik takip + session sektör? → HAFIZA SUCCESS
  → aksi halde → FB (UNCERTAIN veya OOD)
  → intent_router_contract adaptörü → Spec JSON
```

| Bileşen | V1 |
|---------|-----|
| Embedding | `bge-m3` |
| Retrieval | Yerel NPZ / bellek indeksi |
| Reranker | Yok |
| `sub_intent` | Geçici keyword + seed mapper |
| Eşik | `MIN_BGE=0.80`, `MIN_MARGIN=0.06` |
| Latency hedefi | Ölçülür; V2’de &lt; 150ms zorunlu |

### V1 karar önceliği (özet)

1. K1 kısaltma kısa devresi  
2. BGE-M3 skor + sektör margin  
3. Session hafıza (jenerik takip)  
4. Fallback güvenlik ağı  

---

## 4. Hedef durum — V2 Pipeline

```
User Query
  → Query Embedding (bge-m3)
  → PostgreSQL pgvector ANN → Top-3 aday
  → Cross-Encoder rerank (bge-reranker-v2-m3) → final confidence
  → status / sector / sub_intent (rerank sonucu)
  → Spec JSON (aynı sözleşme)
  → Toplam latency MUST < 150ms
```

| Bileşen | V2 (hedef) |
|---------|------------|
| Stage 1 Retrieval | `bge-m3` embedding → `pgvector` → Top-3 |
| Stage 2 Reranking | `bge-reranker-v2-m3` Cross-Encoder |
| Persistence | PostgreSQL (vektör + intent metadata) |
| `sub_intent` | Rerank edilen adayın intent kodu |
| Latency | **&lt; 150ms** uçtan uca |
| Dış sözleşme | V1 ile **aynı** JSON contract |

### V2 iskelet (paralel servis — V1 NPZ bozulmaz)

| Modül | Yol |
|-------|-----|
| Şema / HNSW | `chatbot_demo/src/db/schema.py`, `migrate.py` |
| Bağlantı | `chatbot_demo/src/db/connection.py` |
| ANN store | `chatbot_demo/src/db/vector_store.py` → tablo `vector_index` |
| Reranker | `chatbot_demo/src/models/reranker.py` (`BGEReranker`, lazy singleton) |
| Orkestrasyon | `chatbot_demo/src/v2_pipeline.py` (`V2IntentPipeline`) |
| Seed (clean_v1) | `chatbot_demo/scripts/seed_pgvector.py` |
| Duman testi | `chatbot_demo/scripts/test_reranker_pipeline.py` |
| Postgres | Yerel kurulum, port **5432**, DB `chatbot_db` (`.env`) |

```bash
# Yerel Postgres ayakta olsun; chatbot_demo/.env → localhost:5432/chatbot_db
python -m db_api.setup_local_db
python scripts/seed_pgvector.py
python scripts/test_reranker_pipeline.py
# Postgres yokken: python scripts/test_reranker_pipeline.py --offline-npz
```

### V1 → V2 geçiş ilkeleri

- Dış JSON sözleşmesi değişmez; istemciler kırılmaz.
- `ChatbotResponse` legacy alanları korunur; adaptör V2 skor kaynağına bağlanır.
- `MIN_BGE=0.80` açık talimat olmadan düşürülmez.
- Geçici keyword `sub_intent` mapper, reranker canlıya alınca kaldırılır veya fallback olarak kalır.
- Canlı `Chatbot.sor()` hâlâ V1 NPZ kullanır; V2 `V2IntentPipeline` ile paraleldir.

---

## 5. V1 vs V2 karşılaştırma

| | V1 (şimdi) | V2 (hedef) |
|---|------------|------------|
| Retrieval | NPZ / bellek + BGE-M3 | pgvector + BGE-M3 Top-3 |
| Ranking | Tek aşama (dense skor) | + `bge-reranker-v2-m3` |
| `sub_intent` | Keyword / seed adaptörü | Rerank adayı |
| Depolama | Dosya indeksi + ayrı DB seed | Unified PostgreSQL |
| Latency | Ölçüm var | &lt; 150ms zorunlu |
| Contract | `intent_router_contract` | Aynı contract |

---

## 6. Geliştirme kuralları (özet)

1. Spec çıktısı her zaman `to_intent_router` / `to_intent_router_json` üzerinden üretilir.  
2. Legacy `ChatbotResponse` alanları rename / remove edilmez.  
3. `MIN_BGE` düşürülmez; belirsizlikte `UNCERTAIN` / `OOD`.  
4. V2 işleri (pgvector, reranker) contract’ı bozmadan Stage 1/2 olarak eklenir.  
5. Latency bütçesi V2’de 150ms; yeni adımlar bu bütçeye sığmalıdır.

---

## 7. Örnek çıktılar

**SUCCESS**

```json
{
  "query": "Kardiyoloji randevusu almak istiyorum",
  "intent": {
    "sector": "health",
    "sub_intent": "health.appointment",
    "confidence_score": 0.91
  },
  "status": "SUCCESS",
  "latency_ms": 112
}
```

**UNCERTAIN**

```json
{
  "query": "fiyat teklifi almak istiyorum",
  "intent": {
    "sector": "ood",
    "sub_intent": "ood.none",
    "confidence_score": 0.58
  },
  "status": "UNCERTAIN",
  "latency_ms": 70
}
```

**OOD**

```json
{
  "query": "bugün hava çok güzel",
  "intent": {
    "sector": "ood",
    "sub_intent": "ood.none",
    "confidence_score": 0.08
  },
  "status": "OOD",
  "latency_ms": 40
}
```
