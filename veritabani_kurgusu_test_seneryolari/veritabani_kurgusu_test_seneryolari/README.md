# Chatbot / Bilgi Merkezi — Veritabanı Kurgusu (v6 - Sadeleştirilmiş)

SQLAlchemy modelleri + Alembic migration ortamı. PostgreSQL 16 + pgvector üzerinde tasarlandı.
Tek kaynak dizin: bu klasör (`models.py` ≡ `schema.sql`).

## v6'da Neler Var

- **Köklü Sadeleştirme**: Çoklu model, embedding ve benzerlik skorlarını tutan yardımcı tablolar (similarity_models, company_embeddings, similarity_scores, sector_form_mappings, company_technologies, fallback_contacts) kaldırılarak sistem 11 tabloya düşürülmüştür.
- **Sohbet Yapısı Yenilikleri**: Konuşmalar başlık/oturum eşleşmesi bazında `conversations` tablosunda tutulurken, konuşmaya ait kullanıcı ve bot yanıtları `messages` tablosunda saklanmaktadır.
- **Yönlendirme ve İlişkisel Intent Mimarisi**:
  - `intents` tablosunda her niyet için chatbot'un kullanıcıyı yönlendireceği hedef form veya sayfa bağlantısını saklayan `url` kolonu yer alır. Bu alanın amacı, niyet tespit edildiğinde kullanıcıyı ilgili dış bağlantıya yönlendirmektir.
  - `qa_embeddings` tablosu ile `intents` tablosu arasında `intents (1) └── qa_embeddings (N)` ER ilişkisi kurulmuştur. qa_embeddings tablosundaki `intent_id` alanı, `intent_id -> intents.id` bağlantısı üzerinden niyet kataloğuna referans verir.
- **Vektör Bilgi Bankası**: Embedding yapısı yalnızca soru-cevap ve BGE vektörlerinin tutulduğu `qa_embeddings` tablosunda (1024 boyutlu vektör) aktif durumdadır.
- **Toplam 11 Tablo**: ORM ve DDL katmanları 11 tablo halinde tam senkronize edilmiştir.
- **Event-Based Validation**: Alan atama sırasından etkilenmeyen, nesne seviyesinde kararlı çalışan SQLAlchemy event listener'ları (`before_insert` / `before_update`) sisteme dahil edilmiştir.

---

## Veritabanı Tablo Yapısı (Toplam 11 Tablo)

1. `sectors`: Sektör bilgilerini (iki dilli) saklar.
2. `intents`: Konuşma niyetlerini ve yönlendirme adreslerini (`url`) saklar. `url` alanı, chatbot'un tespit edilen niyete göre kullanıcıya sunacağı hedef form bağlantı adresini barındırır.
3. `admin_users`: Panel yöneticilerini saklar.
4. `blogs`: Dashboard üzerinden yönetilen blog yazılarını (yayın tutarlılık kısıtlı) saklar.
5. `companies`: Şirket bilgilerini saklar.
6. `sessions`: Kullanıcı oturumlarını saklar.
7. `conversations`: Oturum içi konuşma başlıklarını saklar.
8. `messages`: Konuşmadaki kullanıcı ve bot mesaj detaylarını saklar.
9. `qa_embeddings`: Soru-cevap çiftlerini ve BGE embedding vektörlerini saklar. Her kayıt `intent_id -> intents.id` bağıntısıyla ilgili niyete bağlıdır (`intents (1) └── qa_embeddings (N)` ilişkisi).
10. `analytics_events`: Chatbot performans ve yönlendirme analiz olaylarını saklar.
11. `alembic_version`: Veritabanı göç sürümünü saklar.

---

## Hızlı Başlangıç — Yerel PostgreSQL

Yerel Postgres (port **5432**) ayakta olsun. Kullanıcı `postgres`, veritabanı `chatbot_db`.

```bash
# Bağımlılıkları yükleyin
pip install -r requirements.txt

# .env dosyasını kontrol edin (localhost:5432/chatbot_db)
# Migration'ı uygulayarak tabloları oluşturun
alembic upgrade head

# assert'lü akış testini çalıştırın (DB kirletmeden rollback ile çalışır)
python test_flow.py

# Veritabanına mock veri eklemek (commit etmek) için seed scriptini çalıştırın
python seed_mock_data.py
```

---

## Dosya Yapısı

- `.env.example` — Yerel Postgres bağlantı örneği.
- `models.py` — SQLAlchemy modelleri (11 tablo, isimlendirilmiş kısıtlar, event-based doğrulamalar).
- `schema.sql` — Referans DDL (Modellerle 1:1 uyumlu SQL şeması).
- `database.py` — Engine/Session yönetimi (Eksik parametrede doğrudan hata fırlatır).
- `alembic/versions/a1b2c3d4e5f6_initial_complete_schema.py` — Sıfırdan temiz "Initial complete schema" migration dosyası.
- `test_flow.py` — Assert'li akış testi.
- `seed_mock_data.py` — get_or_create mantığıyla çalışan, mükerrer kayda yol açmayan güvenli veri tohumlama scripti.