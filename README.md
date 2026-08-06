# Chatbot Bilgi Merkezi Projesi

Staj / araştırma dokümantasyonu ve **aktif chatbot servisi** tek repoda toplanmıştır. Geliştirme ve demo için tek kaynak:

**[`chatbot_demo/`](chatbot_demo/)** — FastAPI intent router + embed widget

## Klasörler

```
Chatbot_Bilgi_Merkezi_Projesi/
├── requirements.txt        ← Tüm proje Python bağımlılıkları (tek dosya)
├── chatbot_demo/           ← Aktif uygulama (README burada)
├── 01_Raporlar/            ← Staj raporları
├── 02_Toplanti_Notlari/    ← Toplantı notları
├── archive/                ← Eski prototipler (arşiv)
├── docs/                   ← Proje geneli notlar
└── veritabani_kurgusu_test_seneryolari/   ← DB test senaryoları
```

Yerel referans kopyalar (`allintos-main (1)/`, `Allintos/`) repoya dahil değildir (`.gitignore`).

## Çalıştırma

```powershell
pip install -r requirements.txt
cd chatbot_demo
copy .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8082
```

Bağımlılıklar: proje kökündeki **`requirements.txt`** (chatbot + Allintos backend + DB testleri).

Detaylı mimari, Allintos entegrasyonu ve test komutları: **[chatbot_demo/README.md](chatbot_demo/README.md)**
