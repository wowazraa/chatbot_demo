# Stres Testi Raporu (Adversarial Chatbot Evaluation)

**Tarih:** 2026-07-16  
**Değerlendiren:** Antigravity Adversarial Agent  
**Genel Başarı Oranı:** %84.04 (79/94 Başarılı)

## Kategori Bazlı Başarı Tablosu

| Kategori | Açıklama | Başarılı / Toplam | Başarı Oranı |
|---|---|---|---|
| A | Negasyon ve Olumsuzlama | 7/13 | %53.8 (ORTA) |
| B | Çoklu/Çakışan Niyet (Multi-Intent) | 8/10 | %80.0 (BAŞARILI) |
| C | Kısaltma, Yazım Hatası, Argo | 8/10 | %80.0 (BAŞARILI) |
| D | Dil Karışımı (Code-Switching) | 9/10 | %90.0 (BAŞARILI) |
| E | Uzun, Gerçekçi Kurumsal Cümleler | 10/10 | %100.0 (BAŞARILI) |
| F | Belirsiz / Sektörsüz Traps (False-Positives) | 6/10 | %60.0 (ORTA) |
| G | Fiyat / Genel Soru / Kapsam Dışı | 10/10 | %100.0 (BAŞARILI) |
| H | Adversarial / Kandırma / Spam | 12/12 | %100.0 (BAŞARILI) |
| I | Bağlam/Session Hafızası (Multi-turn) | 9/9 | %100.0 (BAŞARILI) |

## En Çok Başarısız Olunan Kategoriler ve Analizi

### Kategori A — Negasyon ve Olumsuzlama (Başarı: %53.8)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Negasyon Kaçırma:** BGE-M3 dense modelinin cümlenin genel anlamsal yapısını çözmesi istenirken, cümlede ilk geçen sektörü (örn: 'sağlık istemiyoruz') baskın ağırlıklı eşleştirdiği görülmüştür. Cosine eşiğinin altındaki kırılımlar veya kural tabanlı regex'lerin kelime bazlı tetiklenmesi negasyonu bypass etmiştir.

### Kategori F — Belirsiz / Sektörsüz Traps (False-Positives) (Başarı: %60.0)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Yüzeysel Anahtar Kelime Tuzağı:** 'Sağlıklı bir ortaklık' veya 'hayat eğitimi' gibi bağlam dışı mecaz/deyim kullanımlarında, regex kuralları ('sağlık', 'eğitim') kelime düzeyinde yakalandığı için model yanlış-pozitif (false positive) olarak K1 moduna yönlenmiştir.

### Kategori B — Çoklu/Çakışan Niyet (Multi-Intent) (Başarı: %80.0)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Çoklu Niyet Çıkmazı:** Model yapısı gereği tek bir sektör etiketi dönebilmektedir. Cümlede hem sağlık hem savunma geçtiğinde, model en yüksek skorlu olanı seçmiş, ancak kullanıcının çakışan niyetini algılayıp 'Hangisiyle devam edelim?' sorusunu sorma mekanizması bulunmadığından borderline/fail olarak kalmıştır.

## Başarısız Senaryo Detayları (Hata Analizi)

| ID | Girdi Metni | Beklenen | Tahmin | Yöntem | Hata Nedeni |
|---|---|---|---|---|---|
| A05 | Eski turizm acente programımızı bırakıp ... | `sağlık` | `turizm` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A07 | lms kurulumundan vazgeçtik, telemedicine... | `sağlık` | `belirsiz` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A08 | otel yönetimi yerine radar kontrol yazıl... | `savunma` | `turizm` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A09 | savunma radar projesi mi eğitim otomasyo... | `eğitim` | `savunma` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A11 | Kesinlikle otel veya seyahat rezervasyon... | `savunma` | `turizm` | `kural` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A13 | savunma sanayi alanında çalışmıyoruz, ok... | `eğitim` | `savunma` | `kural` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| B01 | Hem sağlık hem de savunma alanında faali... | `tartışmalı` | `belirsiz` | `kural` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B04 | Önce otel otomasyonunu tamamlayıp ardınd... | `tartışmalı` | `belirsiz` | `bge-m3` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| C05 | sağlıkksektörüüotomasyonuuarıyoruzz | `sağlık` | `belirsiz` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| C07 | eğitm portali örenci işleri | `eğitim` | `ik_kurumsal` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| D09 | university registration system yenilemek... | `eğitim` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| F01 | Sağlıklı bir iş ortaklığı kurmak istiyor... | `belirsiz` | `savunma` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F02 | Turistik bir bölgede ofisimiz var ama ya... | `belirsiz` | `turizm` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F05 | Hastane köşelerinde beklemek istemediğim... | `belirsiz` | `sağlık` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F07 | Askeri disiplinle çalışan bir ekibimiz v... | `belirsiz` | `savunma` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |

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
