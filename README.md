# Chatbot Bilgi Merkezi Projesi

```
Chatbot_Bilgi_Merkezi_Projesi/
├── 01_Raporlar/              # Staj / araştırma raporları
├── 02_Toplanti_Notlari/      # Toplantı notları
├── archive/                  # Eski kod ve geçmiş test çıktıları
│   ├── 03_Kaynak_Kod/        # Legacy prototipler
│   └── test_ciktilari/       # Arşivlenmiş raporlar
└── chatbot_demo/             # Aktif uygulama (tek kaynak)
    ├── app.py                # Streamlit girişi
    ├── demo/                 # Web demo (server.py + index.html)
    ├── src/                  # Motor (chatbot, embedder, rewriter…)
    ├── data/                 # raw + processed dataset / index
    ├── scripts/              # build_index vb.
    ├── tests/                # Test scriptleri
    │   └── fixtures/         # Senaryo JSON girdileri
    └── reports/              # Test çıktıları (gitignore)
```

Aktif testler: `chaos_monkey`, `the_crucible`, `run_stres_test`, `test_k1_celiski`  
Eski tek-seferlik scriptler: `archive/obsolete_tests/`

## Çalıştırma

```bash
cd chatbot_demo
pip install -r requirements.txt
python demo/server.py          # http://localhost:8080
# veya
streamlit run app.py
```

Detaylar: [`chatbot_demo/README.md`](chatbot_demo/README.md)
