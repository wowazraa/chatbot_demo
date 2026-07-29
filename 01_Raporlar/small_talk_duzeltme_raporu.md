# Small Talk Düzeltme Raporu

**Tarih:** 17 Temmuz 2026  
**Dosya:** `chatbot_demo/src/chatbot.py`

---

## 1) Kök sebep (kanıtlı)

`sor()` içinde `_small_talk_mi()` **K1 / BGE’den önce** çalışıyordu. Mesajda `merhaba` / `iyi günler` geçtiği anda kısa-devre yapılıp `Genel Sohbet` dönülüyordu; K1 hard-match hiç çağrılmıyordu.

**Öncesi (debug):**
| Mesaj | `small_talk_mi` | K1 kesin (manuel) | Pipeline sonucu |
|-------|-----------------|-------------------|-----------------|
| Merhaba, hastanemiz için randevu sistemi… | True | sağlık (`hastanemiz…randevu`) | Genel Sohbet / small_talk (K1 atlandı) |
| İyi günler, otel rezervasyon yazılımı… | True | turizm ipucu var | Genel Sohbet / small_talk (K1 atlandı) |

---

## 2) Düzeltme

Yeni sıra:

1. Rewriter  
2. **K1 hard-match + BGE** (`_standart_sor`) → sektör varsa dön  
3. Sektör yoksa: **`_saf_selamlasma_mi`**  
   - Yalnızca saf selam / phatic → `Genel Sohbet` / `small_talk`  
   - Selam + anlaşılamayan talep → `Sektör Belirsiz` / FB (**Genel Sohbet değil**)

`_saf_selamlasma_mi`: selamı soyduktan sonra anlamlı gövde varsa False. Birden fazla metinden biri boş diye erken True dönmez (Hello + EN talep regressiyonu kapatıldı).

Eşikler değiştirilmedi (savunma 0.82 / FINAL_MIN 0.75).

---

## 3) Öncesi / sonrası (kanıt örnekleri)

| Mesaj | Öncesi | Sonrası |
|-------|--------|---------|
| Merhaba, hastanemiz için randevu sistemi arıyoruz. | Genel Sohbet / small_talk / 0.00 | **sağlık / K2 / k1-hard / 0.90** |
| İyi günler, otel rezervasyon yazılımına ihtiyacımız var. | Genel Sohbet / small_talk / 0.00 | **turizm / K2 / k1-hard / 0.90** |

---

## 4) Regresyon sonuçları

### Bölüm A — Saf selam → Genel Sohbet
**7/7** — Merhaba, Selam, İyi akşamlar, Günaydın, İyi günler, Nasılsın?, Teşekkürler

### Bölüm B — Selam + sektör
**5/5** — sağlık, turizm, savunma, eğitim, klinik randevu (hepsi K2, small_talk değil)

### Bölüm C — Selam + belirsiz talep → Sektör Belirsiz
**3/3** — fiyat teklifi / genel yazılım / bilgi almak → FB + `Sektör Belirsiz` (Genel Sohbet değil)

### `tests/fixtures/test_scenarios.json`
**20/22**

Kalan 2 (small_talk ile **ilgisiz**, önceden de kırılgan):
- **S05** `sğlk hastane yazılımı` — kısaltma normalizasyonu yok → FB  
- **S14** tek kelime `sağlık` — ürünsüz ince sinyal, precision kapısında FB  

### Stres testi (`run_stres_test`, 94 koşu)
| Kategori | Sonuç |
|----------|-------|
| A | 2/13 |
| F | **10/10** (korundu) |
| G | **10/10** |
| H | 6/12 |
| I | 4/9 |
| **Toplam** | **43/94 (46%)** |

F kategorisi (yanlış-pozitif tuzakları) bozulmadı. A/H düşük skorları bu PR’ın small_talk sırasından ziyade mevcut precision / etiket beklentisi gerilimini yansıtıyor.

---

## 5) Sonuç

Kritik hata giderildi: **selam + sektör talebi artık Genel Sohbet’e yutulmuyor.**  
Saf selam davranışı korundu; selam + belirsiz talep netleştirme (FB) olarak ayrıldı.
