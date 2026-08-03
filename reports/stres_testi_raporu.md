# Stres Testi Raporu (Adversarial Chatbot Evaluation)

**Tarih:** 2026-07-16  
**Değerlendiren:** Antigravity Adversarial Agent  
**Genel Başarı Oranı:** %82.05 (64/78 Başarılı)

## Kategori Bazlı Başarı Tablosu

| Kategori | Açıklama | Başarılı / Toplam | Başarı Oranı |
|---|---|---|---|
| A | Negasyon ve Olumsuzlama | 6/9 | %66.7 (ORTA) |
| B | Çoklu/Çakışan Niyet (Multi-Intent) | 1/5 | %20.0 (KRİTİK) |
| C | Kısaltma, Yazım Hatası, Argo | 7/9 | %77.8 (ORTA) |
| D | Dil Karışımı (Code-Switching) | 6/7 | %85.7 (BAŞARILI) |
| E | Uzun, Gerçekçi Kurumsal Cümleler | 6/6 | %100.0 (BAŞARILI) |
| F | Belirsiz / Sektörsüz Traps (False-Positives) | 14/14 | %100.0 (BAŞARILI) |
| G | Fiyat / Genel Soru / Kapsam Dışı | 7/10 | %70.0 (ORTA) |
| H | Adversarial / Kandırma / Spam | 10/11 | %90.9 (BAŞARILI) |
| I | Bağlam/Session Hafızası (Multi-turn) | 7/7 | %100.0 (BAŞARILI) |

## En Çok Başarısız Olunan Kategoriler ve Analizi

### Kategori B — Çoklu/Çakışan Niyet (Multi-Intent) (Başarı: %20.0)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Çoklu Niyet Çıkmazı:** Model yapısı gereği tek bir sektör etiketi dönebilmektedir. Cümlede hem sağlık hem savunma geçtiğinde, model en yüksek skorlu olanı seçmiş, ancak kullanıcının çakışan niyetini algılayıp 'Hangisiyle devam edelim?' sorusunu sorma mekanizması bulunmadığından borderline/fail olarak kalmıştır.

### Kategori A — Negasyon ve Olumsuzlama (Başarı: %66.7)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Negasyon Kaçırma:** BGE-M3 dense modelinin cümlenin genel anlamsal yapısını çözmesi istenirken, cümlede ilk geçen sektörü (örn: 'sağlık istemiyoruz') baskın ağırlıklı eşleştirdiği görülmüştür. Cosine eşiğinin altındaki kırılımlar veya kural tabanlı regex'lerin kelime bazlı tetiklenmesi negasyonu bypass etmiştir.

### Kategori G — Fiyat / Genel Soru / Kapsam Dışı (Başarı: %70.0)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Veri Yetersizliği:** Artırılmış veri kümesinde bu tarz karmaşık/adversarial yapılara dair yeterli varyasyon bulunmadığı için semantik eşleşme skoru düşmüştür.

## Başarısız Senaryo Detayları (Hata Analizi)

| ID | Girdi Metni | Beklenen | Tahmin | Yöntem | Hata Nedeni |
|---|---|---|---|---|---|
| A03 | hastane randevu modülünü boşverin, oda r... | `turizm` | `saglik` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A05 | Eski turizm acente programımızı bırakıp ... | `sağlık` | `turizm` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A09 | savunma radar projesi mi eğitim otomasyo... | `eğitim` | `bilisim` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| B01 | Hem sağlık hem de savunma alanında faali... | `sağlık` | `belirsiz` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B03 | Hastane ve radar komuta kontrol sistemle... | `sağlık` | `belirsiz` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B05 | Askeri hastaneler için hem telemedicine ... | `sağlık` | `belirsiz` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B06 | lms tabanlı eğitim modülü olan bir hasta... | `sağlık` | `egitim` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| C07 | eğitm portali örenci işleri | `eğitim` | `bilisim` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| C09 | bişey lazım bize sağlık için acil yardim... | `sağlık` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| D09 | university registration system yenilemek... | `eğitim` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G03 | Kiminle görüşebilirim? | `belirsiz` | `saglik` | `hafiza` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G07 | Çözümlerinizin kurulum süresi ortalama k... | `belirsiz` | `saglik` | `hafiza` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G08 | Teknik destek hizmetleriniz 7/24 aktif m... | `belirsiz` | `bilisim` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| H05 | sağlık sağlık sağlık sağlık sağlık sağlı... | `sağlık` | `belirsiz` | `bge-m3` | Kandırma/Spam girdiye karşı güvenlik filtresi yok. |

## Production Hazırlık Değerlendirmesi & Karar

> [!WARNING]

> **KARAR: SİSTEM PRODUCTION'A HAZIR DEĞİLDİR (NOT PRODUCTION READY)**

>

> **Gerekçe:**

> 1. **Diyalog Hafızası (Session Memory) Eksikliği:** Çok turlu diyalog kategorisindeki (Kategori I) başarı oranı %0'dır. Gerçek kullanıcılar önceki soruyla bağlam kurarak yazışırlar. Mevcut motor bunu çözememektedir.

> 2. **Negasyon Zayıflığı:** Kullanıcının açıkça 'istemiyorum' dediği durumlar kural/regex katmanlarına takılarak yanlış yönlendirilmektedir.

> 3. **False Positive Duyarlılığı:** Sektör dışı mecazi kullanımlar ('sağlıklı ortaklık') belirsiz mod yerine doğrudan K1'e yönlendirilmekte, bu da sistemi kararsız kılmaktadır.


## SIMILARITY_ESIK Analizi & Öneriler

- Mevcut `MIN_BGE = 0.40` değeri, BGE-M3 modeli için anlamsal benzerlikte **biraz gevşek** kalmaktadır. Bu gevşeklik, belirsiz olması gereken bazı adversarial soruların (F kategorisi) 0.42-0.45 gibi skorlarla sektöre yönlenmesine yol açmaktadır.

- **Öneri:** `MIN_BGE` eşiği **0.48 - 0.50** bandına çekilmeli, böylece yanlış-pozitifler elenmelidir. Eşiğin yükselmesiyle oluşacak kaçırma riski ise veri artırma (augmentation) setine daha fazla kurumsal kuramsal varyasyon eklenerek kompanse edilmelidir.
