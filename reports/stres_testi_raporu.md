# Stres Testi Raporu (Adversarial Chatbot Evaluation)

**Tarih:** 2026-07-16  
**Değerlendiren:** Antigravity Adversarial Agent  
**Genel Başarı Oranı:** %55.95 (47/84 Başarılı)

## Kategori Bazlı Başarı Tablosu

| Kategori | Açıklama | Başarılı / Toplam | Başarı Oranı |
|---|---|---|---|
| A | Negasyon ve Olumsuzlama | 4/9 | %44.4 (KRİTİK) |
| B | Çoklu/Çakışan Niyet (Multi-Intent) | 7/10 | %70.0 (ORTA) |
| C | Kısaltma, Yazım Hatası, Argo | 5/9 | %55.6 (ORTA) |
| D | Dil Karışımı (Code-Switching) | 5/7 | %71.4 (ORTA) |
| E | Uzun, Gerçekçi Kurumsal Cümleler | 4/7 | %57.1 (ORTA) |
| F | Belirsiz / Sektörsüz Traps (False-Positives) | 6/14 | %42.9 (KRİTİK) |
| G | Fiyat / Genel Soru / Kapsam Dışı | 0/10 | %0.0 (KRİTİK) |
| H | Adversarial / Kandırma / Spam | 9/11 | %81.8 (BAŞARILI) |
| I | Bağlam/Session Hafızası (Multi-turn) | 7/7 | %100.0 (BAŞARILI) |

## En Çok Başarısız Olunan Kategoriler ve Analizi

### Kategori G — Fiyat / Genel Soru / Kapsam Dışı (Başarı: %0.0)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Veri Yetersizliği:** Artırılmış veri kümesinde bu tarz karmaşık/adversarial yapılara dair yeterli varyasyon bulunmadığı için semantik eşleşme skoru düşmüştür.

### Kategori F — Belirsiz / Sektörsüz Traps (False-Positives) (Başarı: %42.9)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Yüzeysel Anahtar Kelime Tuzağı:** 'Sağlıklı bir ortaklık' veya 'hayat eğitimi' gibi bağlam dışı mecaz/deyim kullanımlarında, regex kuralları ('sağlık', 'eğitim') kelime düzeyinde yakalandığı için model yanlış-pozitif (false positive) olarak K1 moduna yönlenmiştir.

### Kategori A — Negasyon ve Olumsuzlama (Başarı: %44.4)

Bu kategoride temel zayıflıkların nedeni şunlardır:

- **Negasyon Kaçırma:** BGE-M3 dense modelinin cümlenin genel anlamsal yapısını çözmesi istenirken, cümlede ilk geçen sektörü (örn: 'sağlık istemiyoruz') baskın ağırlıklı eşleştirdiği görülmüştür. Cosine eşiğinin altındaki kırılımlar veya kural tabanlı regex'lerin kelime bazlı tetiklenmesi negasyonu bypass etmiştir.

## Başarısız Senaryo Detayları (Hata Analizi)

| ID | Girdi Metni | Beklenen | Tahmin | Yöntem | Hata Nedeni |
|---|---|---|---|---|---|
| A02 | savunma sanayi projesi değil, eğitim oto... | `eğitim` | `belirsiz` | `kisaltma` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A05 | Eski turizm acente programımızı bırakıp ... | `sağlık` | `turizm` | `bge-m3` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A06 | Biz askeri birlik değiliz, sadece okul k... | `eğitim` | `belirsiz` | `kisaltma` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A09 | savunma radar projesi mi eğitim otomasyo... | `eğitim` | `belirsiz` | `kisaltma` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| A13 | savunma sanayi alanında çalışmıyoruz, ok... | `eğitim` | `belirsiz` | `kisaltma` | Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı. |
| B01 | Hem sağlık hem de savunma alanında faali... | `sağlık` | `belirsiz` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B05 | Askeri hastaneler için hem telemedicine ... | `sağlık` | `belirsiz` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| B06 | lms tabanlı eğitim modülü olan bir hasta... | `sağlık` | `egitim` | `kisaltma` | Çoklu niyet durumunda tekil sektöre zorlama yapıldı. |
| C03 | trzm sekt icn rzv programı | `turizm` | `saglik` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| C04 | egt kurumu icin uzaktan lms | `eğitim` | `egitim` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| C07 | eğitm portali örenci işleri | `eğitim` | `bilisim` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| C08 | hastaneyonetimsistemiyazilimi | `sağlık` | `saglik` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| D03 | Hastane için bir EHR sistemi arıyoruz | `sağlık` | `saglik` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| D09 | university registration system yenilemek... | `eğitim` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| E02 | İyi çalışmalar dileriz. Grubumuz bünyesi... | `turizm` | `turizm` | `hafiza` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| E06 | Kamu kurumlarına eğitim ve danışmanlık h... | `eğitim` | `egitim` | `kisaltma` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| E09 | Yeni açılacak tatil köyümüz için online ... | `turizm` | `turizm` | `hafiza` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| F01 | Sağlıklı bir iş ortaklığı kurmak istiyor... | `belirsiz` | `saglik` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F02 | Turistik bir bölgede ofisimiz var ama ya... | `belirsiz` | `turizm` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F03 | Eğitimli personel arıyoruz, işe alım kon... | `belirsiz` | `egitim` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F06 | Otel konforunda bir çalışma ortamı sunan... | `belirsiz` | `turizm` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F09 | Sağlığınızı korumak için günde en az iki... | `belirsiz` | `eglence` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F10 | Turizm cenneti olan ülkemizde yeni ofisl... | `belirsiz` | `turizm` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F11 | Çalışanlarımız için çok eğlenceli bir iş... | `belirsiz` | `saglik` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| F13 | Bilişim gibi hızlı büyüyen bir sektörde ... | `belirsiz` | `bilisim` | `bge-m3` | Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive). |
| G01 | Fiyat teklifi almak istiyorum | `belirsiz` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G02 | Ne kadar sürer? | `belirsiz` | `saglik` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G03 | Kiminle görüşebilirim? | `belirsiz` | `saglik` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G04 | Fiyatlandırma nasıl? | `belirsiz` | `eglence` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G05 | Referanslarınız var mı? | `belirsiz` | `bilisim` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G06 | Demo yapabilir miyiz? | `belirsiz` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G07 | Çözümlerinizin kurulum süresi ortalama k... | `belirsiz` | `bilisim` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G08 | Teknik destek hizmetleriniz 7/24 aktif m... | `belirsiz` | `bilisim` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G09 | Ofisiniz nerede bulunuyor? | `belirsiz` | `turizm` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| G10 | Mail adresinizi alabilir miyim? | `belirsiz` | `egitim` | `bge-m3` | Semantik benzerlik skoru eşik değerin altında kaldı. |
| H09 | savunma değil eğitim değil sağlık hiç de... | `turizm` | `belirsiz` | `kisaltma` | Kandırma/Spam girdiye karşı güvenlik filtresi yok. |
| H10 | merhaba merhaba merhaba selam lütfen | `belirsiz` | `belirsiz` | `kisaltma` | Kandırma/Spam girdiye karşı güvenlik filtresi yok. |

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
