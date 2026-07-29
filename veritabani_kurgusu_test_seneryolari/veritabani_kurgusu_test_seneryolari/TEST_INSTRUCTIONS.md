# Veritabanı Bütünlük Testleri

Bu ekleme mevcut proje dosyalarını silmez veya değiştirmez. Yalnızca aşağıdaki iki yeni dosya eklenmiştir:

- `test_database_integrity.py`
- `TEST_INSTRUCTIONS.md`

Testler gerçek PostgreSQL veritabanında çalışır fakat her test ayrı transaction kullanır ve sonunda rollback yapar. Kalıcı test verisi bırakmaz.

## Yerel Postgres ile çalıştırma

```powershell
# Yerel Postgres (5432) + .env hazır olsun
alembic upgrade head
python -m unittest -v test_database_integrity.py
```

## Beklenen sonuç

Aşağıdaki testlerin başarılı olması beklenir:

- Session silinince conversation ve analytics kayıtlarının CASCADE ile silinmesi
- Conversation silinince messages kayıtlarının CASCADE ile silinmesi
- Geçersiz message rolünün reddedilmesi
- Mükerrer sector_key ve intent_code değerlerinin reddedilmesi
- Yayınlanmış blog için published_at zorunluluğu

`qa_embeddings` boş question/answer testi `expected failure` olarak işaretlenmiştir. Bunun nedeni mevcut şemada `nullable=False` bulunmasına rağmen boş metni engelleyen bir CHECK constraint olmamasıdır. Bu durum test çıktısında görünür ancak diğer testleri durdurmaz.
