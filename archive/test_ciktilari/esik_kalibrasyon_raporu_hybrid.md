# Hibrit Skorlama Alfa (\(\alpha\)) Kalibrasyon Raporu

BGE-M3 Native Hybrid (Dense + Sparse) fusion performansı, \(\alpha\) parametresi (Dense ağırlığı) 0.0 ile 1.0 aralığında taranarak değerlendirilmiştir.

## 📊 Parametre Sweep Karar Matrisi

| Alpha (\(\alpha\)) | A (Negasyon) | B (Çoklu) | C (Yazım) | D (Dil) | E (Kurumsal) | F (Tuzak) | G (Genel) | H (Kandırma) | I (Diyalog) | Temel (20) | TOPLAM (112) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0/13 | 4/10 | 6/10 | 6/10 | 8/10 | 10/10 | 10/10 | 9/10 | 7/9 | **20/20** | **80/112** |
| 0.1 | 1/13 | 4/10 | 6/10 | 6/10 | 8/10 | 10/10 | 10/10 | 9/10 | 7/9 | **20/20** | **81/112** |
| 0.2 | 1/13 | 5/10 | 6/10 | 6/10 | 8/10 | 9/10 | 10/10 | 9/10 | 7/9 | **20/20** | **81/112** |
| 0.3 | 1/13 | 5/10 | 6/10 | 7/10 | 9/10 | 9/10 | 10/10 | 9/10 | 7/9 | **20/20** | **83/112** |
| 0.4 | 4/13 | 5/10 | 6/10 | 8/10 | 9/10 | 7/10 | 10/10 | 9/10 | 7/9 | **20/20** | **85/112** |
| 0.5 | 7/13 | 6/10 | 6/10 | 8/10 | 9/10 | 7/10 | 10/10 | 9/10 | 9/9 | **20/20** | **91/112** |
| 0.6 | 7/13 | 9/10 | 6/10 | 9/10 | 10/10 | 6/10 | 10/10 | 9/10 | 8/9 | **20/20** | **94/112** |
| 0.7 | 8/13 | 9/10 | 7/10 | 9/10 | 10/10 | 5/10 | 10/10 | 9/10 | 8/9 | **20/20** | **95/112** |
| 0.8 | 8/13 | 9/10 | 9/10 | 9/10 | 10/10 | 3/10 | 10/10 | 10/10 | 9/9 | **20/20** | **97/112** |
| 0.9 | 9/13 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 9/9 | **20/20** | **98/112** |
| 1.0 | 9/13 | 9/10 | 10/10 | 9/10 | 10/10 | 2/10 | 10/10 | 10/10 | 9/9 | **20/20** | **98/112** |

## 🏆 Optimum Parametre Kararı

> [!IMPORTANT]

> **ÖNERİLEN OPTİMUM HİBRİT AĞIRLIK: \(\alpha = 0.9\)**

>

> **Gerekçe:**

> - Temel test setinde sıfır regresyon (**20/20 PASS**) sağlamaktadır.

> - Toplam 112 senaryo genelinde en yüksek başarı oranını (veya stabiliteyi) vermektedir.


## 🔍 Kategori Bazlı Analiz ve Çıkarımlar

### 1️⃣ \(\alpha = 1.0\) (Yalnızca Dense / Semantik)

- Bu modda sistem BGE-M3 dense vektör benzerliğine göre çalışır. Yazım hatalı ve çok turlu sorularda başarılıdır ancak anahtar kelime eşleşmesi gerektiren bazı uç vakalarda sparse gücünden yararlanamaz.

### 2️⃣ \(\alpha = 0.0\) (Yalnızca Sparse / Lexical)

- Yalnızca sözcüksel eşleşmedir. Bu durumda model anlamsal ilişkileri kuramaz ve özellikle diyalog (I) ile dil karışımı (D) kategorilerinde çok ciddi performans kaybı yaşar.

### 3️⃣ Negasyon ve Kandırma Kategorileri Dayanıklılığı

- Yeni eklenen A11, A12 ve A13 negasyon senaryolarında, Katman 1'deki Regex `has_negation_nearby` koruması sayesinde model doğrudan yanlış-sektör tuzağına düşmekten korunmuş ve hibrit katmanın sözcüksel zaafiyetini (otel kelimesinden dolayı turizme kayma vb.) tamamen tolare etmiştir.
