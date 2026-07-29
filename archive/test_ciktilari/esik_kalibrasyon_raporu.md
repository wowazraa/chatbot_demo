# Eşik Kalibrasyon Raporu (MIN_BGE Parameter Sweep)

BGE-M3 modelinin anlamsal cosine benzerlik barajı (`MIN_BGE`) 0.40 ile 0.70 aralığında taranmış ve 109 test senaryosu üzerindeki performansı ölçülmüştür.

## 📊 Parametre Sweep Karar Matrisi

| MIN_BGE | A (Negasyon) | B (Çoklu) | C (Yazım) | D (Dil) | E (Kurumsal) | F (Tuzak) | G (Genel) | H (Kandırma) | I (Diyalog) | Temel (20) | TOPLAM (109) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.40 | 7/10 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 5/9 | **20/20** | **92/109** |
| 0.45 | 7/10 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 5/9 | **20/20** | **92/109** |
| 0.50 | 7/10 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 5/9 | **20/20** | **92/109** |
| 0.55 | 7/10 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 5/9 | **20/20** | **92/109** |
| 0.60 | 8/10 | 9/10 | 9/10 | 9/10 | 10/10 | 3/10 | 10/10 | 9/10 | 5/9 | **20/20** | **92/109** |
| 0.65 | 7/10 | 8/10 | 8/10 | 9/10 | 10/10 | 3/10 | 10/10 | 9/10 | 5/9 | **20/20** | **89/109** |
| 0.70 | 7/10 | 9/10 | 7/10 | 9/10 | 10/10 | 3/10 | 10/10 | 8/10 | 5/9 | **20/20** | **88/109** |

## 🔍 Parametre Sweep Bulguları ve Analiz

### 1️⃣ Regresyon Sınırı ve Kararlılık (Regression Boundary)

- **Temel Test Setinde (20/20):** `0.40` ile `0.70` arasındaki tüm eşik değerlerinde **20/20 PASS (%100 başarı)** korunmuştur. Bu durum, temel test setindeki semantik eşleşmelerin çok net ve yüksek skorlu (0.85+) olduğunu kanıtlar.

- **Stres Test Setinde Regresyon:** `MIN_BGE = 0.65` eşiğine ulaşıldığında, stres testindeki doğru sayısı **72'den 69'a düşmektedir.** C ve H kategorilerinde bazı doğru semantik eşleşmeler elendiği için stres testinde regresyon başlamaktadır. Bu yüzden **0.65 ve üzeri değerler üretim için risklidir.**

### 2️⃣ B/D/E Başarı Davranışı

- **E (Uzun Kurumsal)** kategorisi taranan tüm aralıklarda (`0.40 - 0.70`) **%100** kararlılıkla çalışmaya devam etmektedir.
- **D (Dil Karışımı)** kategorisi tüm aralıklarda **%90** kararlılığını korumaktadır.
- Bu durum, gerçek kurumsal niyetlerin BGE-M3 tarafından üretilen benzerlik skorlarının oldukça yüksek (0.75+) olduğunu ve kolay elenmediğini gösterir.

### 3️⃣ F Kategorisinin (Yanlış-Pozitif Tuzakları) İyileşme Eğrisi

- F kategorisinde (Belirsiz olması gereken trap'ler) başarı oranı `0.40 - 0.55` aralığında **2/10 (%20)** seviyesindedir.
- `MIN_BGE = 0.60` eşiğine çıkıldığında ise başarı oranı **3/10 (%30)** seviyesine yükselmektedir (F05 kurtarılmıştır).

### 4️⃣ Önerilen Optimum Eşik Değeri

> [!IMPORTANT]

> **ÖNERİLEN PARAMETRE: `MIN_BGE = 0.50`**

>

> **Gerekçe:**

> - **Güvenlik Marjı:** `0.50` değeri, temel test setinde sıfır regresyon sağlarken BGE-M3 için anlamsal gürültüleri filtreleyecek dengeli bir barajdır.

> - **Maksimum Skor:** En yüksek doğru kararı (**92/109 - %84.4**) stabil bir şekilde vermektedir.

> - **Düşük Risk:** 0.60 ve üzeri eşiklerde C (yazım hatası) ve H (kandırma) gibi katmanların anlamsal doğrulukları düşmeye başladığı için `0.50` en güvenli limandır.

### 5️⃣ Kalan Kalıcı Zayıflıklar (Eşikle Çözülemeyenler)

Önerilen `0.50` eşiğinde bile başarısız olan 17 senaryo:

1. **Kategori I (Multi-turn - 4 Hata):** `I02`, `I04`, `I05`, `I07`. Durumsuzluk (stateless) kaynaklıdır. Eşikten bağımsız olarak session tracking gerektirir.

2. **Kategori A (Negasyon - 3 Hata):** `A03`, `A08`, `A10`. BGE-M3 negasyon kelimesini cosine benzerliğinde ayırt edememektedir. Veri kümesine negasyonlu kurumsal örnekler eklenerek çözülmelidir.

3. **Kategori F (Traps - 8 Hata):** `F01`, `F02`, `F04`, `F05`, `F06`, `F07`, `F08`, `F10`. BGE-M3 benzerliği `0.58` ile `0.76` arasında yüksek skorlar ürettiği için eşik yükselse de yanlış pozitif kalmıştır. Bu kelime mecazları (`iş ortaklığı`, `savunma mekanizması`) veri seti ön temizliğinde genişletilmelidir.
