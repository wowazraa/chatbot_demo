# Proje Final Teslim Dokümanı (Chatbot Bilgi Merkezi)

Bu doküman, Chatbot B2B Niyet Yönlendirme (Intent Routing) altyapısının final sürümüne ait teknik mimariyi, başarı oranlarını ve bilinen kısıtları özetlemektedir.

## 1. Mimari Özeti
Sistem, kullanıcının girdiği metni **5 temel B2B sektörel kategoriye** (sağlık, eğitim, bilişim, turizm, eğlence) veya "belirsiz" (fallback) statüsüne atamak için çok katmanlı (hybrid) bir yapı kullanır. ("Savunma" sektörü bu projede bilinçli olarak desteklenmemektedir ve güvenlik/kısıtlı alan kuralları gereği OOD reddedilmektedir.)

- **Aşama 1 (Hafıza / Session State):** Kullanıcının önceki turda belirlenmiş geçerli bir `aktif_sektor`'ü varsa ve yeni girdi küçük bir takip sorusuysa (örn: "Peki başka neler var?", "Fiyat alabilir miyim?"), sistem BGE-M3'ü pas geçerek doğrudan `HAFIZA` modunda önceki sektörü döndürür.
- **Aşama 2 (K1 Guardrails & Kural Motoru):** Hızlı reddetme (chit-chat, hava durumu vb.) ve **yasaklı kelime (savunma sanayi vs.)** kontrolleri Regex ile yapılır. Savunma talepleri burada bloke edilir. Aynı zamanda kesin sektör kısaltmaları (LMS, HIS vb.) tespit edilirse anında ilgili sektöre yönlendirilir.
- **Aşama 3 (K2 Vektör Veritabanı - BGE-M3):** K1'den geçen metinler BAAI/bge-m3 modeliyle vektörel (1024 boyutlu) embedding'e dönüştürülür. Geliştirme/test ortamında tamamen doğrulanmış olan güncel mimaride yerel `embeddings.npz` indeksi üzerinden kosinüs benzerliği ile en yakın 5 kayıt (Top-K) aranır. (Canlı sistemdeki PostgreSQL `vector_index` / `qa_embeddings` tablolarına yönelik sorgu yapısı teorik olarak kurgulanmış olup henüz bu ortamda stres testine girmemiştir).
- **Aşama 4 (Konsensüs & Fallback):** Top-K sonuçlarının skorları ve ağırlıkları toplanarak en olası sektör seçilir. Skor `0.65` eşiğinin altındaysa veya birden fazla sektör arasında kararsızlık yaşanıyorsa, sistem "belirsiz" (Fallback - FB) moduna düşer ve kullanıcıya genel B2B formunu sunar.
- **Aşama 5 (Session Memory Fallback & Trap Koruması):** OOD (Out of Domain) veya "belirsiz" sınırında kalan düşük skorlu (`s1 >= 0.40`) girdiler için son bir kurtarma denemesidir. Eğer `session_id` içerisinde daha önce doğrulanmış bir `aktif_sektor` varsa, sistem o bağlamı kullanarak OOD kararını sektöre zorlar. Ancak bu işlem, aşırı genelleme hatalarını (Aşama-5-trap) önlemek için `trap_keywords` (iş ortaklığı, personel arıyoruz vb.) kara listesiyle korunmaktadır.
- **Aşama 6 (Aktif Öğrenme Günlüğü / Active Learning):** Tüm kurtarma adımlarına (Aşama 5 dahil) rağmen sistem nihai olarak "belirsiz" (FB) kararı verdiyse, bu zor/anlaşılamayan sorgu `src/unresolved_logger.py` mekanizması tarafından otomatik olarak loglanır (`logs/unresolved_queries.json`). Bu JSONL logları, içerdiği aday (top-candidate) skorlarıyla birlikte BGE-M3 veri setinin zenginleştirilmesi ve ileride "zero-shot" hatalarının giderilmesi için kalıcı bir geri bildirim döngüsü (feedback loop) oluşturur.

## 2. Final Doğrulanmış Skor (North Star Metriği)
Yalnızca hedeflenen sektörün doğru bulunup bulunmadığına bakan (yöntem/mod kısıtlamalarından arındırılmış) son başarı skoru: **147 / 165 (%89.1)**

**Kategori Kırılımları:**
- **TEMEL (19 Senaryo):** 17/19 (%89.5)
- **STRES (78 Senaryo):** 66/78 (%84.6)
- **CEKIM (26 Senaryo):** 26/26 (%100)
- **SELAM (26 Senaryo):** 24/26 (%92.3)
- **K1REG (Hafıza) (16 Senaryo):** 14/16 (%87.5)

## 3. Bilinen Sınırlamalar ve Açık Kalan Sorunlar (Teknik Borçlar)
- **K2 Semantik Kayması (A09):** İçinde "radar" ve "otomasyon" gibi kelimeler geçen ancak aslen eğitim sektörünü hedefleyen (ör. "savunma radar projesi değil, eğitim otomasyonu") girdiler, BGE-M3 modeli tarafından vektörel ortalama nedeniyle yüksek skorla "bilişim" sektörüne atanabilmektedir. Bunun çözümü vektör veri tabanına sentetik örnekler eklemektir.
- **Minör Hafıza ve Selamlaşma Hataları:** SL-C2 ve SL-D1b gibi bazı kompleks bağlam geçişlerinde veya kısa selamlaşmalarda beklenen "belirsiz" yerine rastgele bir sektöre (ör. bilişim) kaymalar yaşanmaktadır.
- **Veritabanı Tablo Ayrımı:** Geliştirme ortamında (testlerde) embedding indeksleri üzerinden simülasyon yapılmaktadır. Canlı `/api/chat` endpoint'inde `qa_embeddings` ile `vector_index` PostgreSQL tablolarının ayrı ayrı kullanılması ve uçtan uca doğrulanması henüz canlı sistem üzerinde stres testine tabi tutulmamıştır.
- **Widget Entegrasyonu:** `demo/` klasöründeki frontend widget'ı (JS/CSS) bağımsız olarak (`localhost:8080`) çalışmakta olup, bilinçli bir tercih olarak Allintos ana yapısına gömülmemiştir.

## 4. Nasıl Çalıştırılır
Nihai testleri ve doğrulama raporlarını çalıştırmak için proje kök dizininde (`chatbot_demo`) aşağıdaki komutları kullanabilirsiniz:

```bash
# Kapsamlı (TEMEL, STRES, SELAM, HAFIZA) Test
python _final_dogrulama.py

# Çekim Eki Tolerans Testi
python tests/run_cekim_eki_orijinal.py

# Demo Widget Sunucusunu Başlatma
python demo/server.py
```
