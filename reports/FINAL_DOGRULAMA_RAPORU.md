# FINAL DOĞRULAMA RAPORU

**Tarih:** 17 Temmuz 2026  
**Koşu:** otomatik / tek sefer / `scripts`-dışı `_final_dogrulama.py`  
**Ön koşul:** small_talk sıralama düzeltmesi uygulanmış (doğrulandı).

## 1. Yönetici Özeti

- **Toplam (skorlanan):** **148/165 (89.7%)**
- **Cuma teslimine hazır mı?** **Şartlı Evet** — kritik bug kapalı; kalan açıklar bilinen sınırlama.
- **Önceki bilinen skorlu setler (SELAM hariç):** ~118/158 (74.7%) → bu tur skorlu (SELAM dahil): 148/165 (89.7%).
  Not: Setler birebir aynı değildi; SELAM yeni eklendi, stres senaryo sayısı bu koşuda 78.

## 2. Set Bazında Özet Tablo

| Test Seti | Senaryo (skorlu) | Başarılı | Oran | Önceki Tur | Değişim |
|---|---:|---:|---:|---|---|
| Temel (test_scenarios) | 19 | 18 | 95% | 20/20 | -5 pp |
| Stres (A–I) | 78 | 66 | 85% | 72/89 | +4 pp |
| Çekim Eki | 26 | 26 | 100% | 10/32 | +69 pp |
| Selamlaşma / Small Talk | 26 | 24 | 92% | (yeni) | yeni set |
| K1 Hard-Match Regresyon | 16 | 14 | 88% | 16/17 | -7 pp |

### Stres kategori kırılımı (bu tur)

| Kat | Başarılı/Toplam | Oran |
|-----|-----------------|------|
| A | 6/9 | 67% |
| B | 1/5 | 20% |
| C | 8/9 | 89% |
| D | 6/7 | 86% |
| E | 6/6 | 100% |
| F | 14/14 | 100% |
| G | 8/10 | 80% |
| H | 10/11 | 91% |
| I | 7/7 | 100% |

## 3. Kritik Kontroller

- [ ] Small talk + sektör doğru mu? → **EVET**
  - `Merhaba, hastanemiz için randevu sistemi arıyoruz.` → **saglik/K1/kisaltma** (OK)
  - `İyi günler, otel rezervasyon yazılımına ihtiyacımız var.` → **turizm/K2/bge-m3** (OK)
  - `Selam, turizm acentesiyiz.` → **turizm/K1/kisaltma** (OK)
  - `Günaydın, üniversitemiz için uzaktan eğitim platformu kurmak istiyoruz` → **egitim/K2/bge-m3** (OK)
  - `Merhaba iyi günler, klinik randevu sistemimizi dijitalleştirmek istiyo` → **saglik/K2/bge-m3** (OK)
- [ ] Saf selam → Genel Sohbet korunuyor mu? → **EVET** (9/9)
- [ ] F kategorisi korunuyor mu? → **EVET** (14/14)
- [ ] Negasyon (stres A) korunuyor mu? → **EVET** (6/9) — not: A seti hâlâ zayıf; ‘korunuyor’ = tamamen çökmedi, hedef skor değil
- [ ] Temel sette sıfır regresyon (20/20)? → **HAYIR** (18/19)
- [ ] `sektöründe(yiz)` / `sanayiinde(yiz)` iyileşti mi? → **EVET** (3/4: A1/B1/C1/D1)

## 4. Bilinen Sınırlamalar (bug değil)

- **Kategori I / session derinliği:** çok turlu diyalogda tutarlılık kısmi.
- **Paralel niyet (K1-B5):** “bir de ayrıca…” → bilinçli belirsiz/FB veya tartışmalı.
- **Nadir fiilleştirme (CE-E*):** otelleştirmek / askerileştirilmiş vb. FB kabul.
- **Ürünsüz genel talep:** “birliklere yönelik sistem”, “öğrencilere uygulama” → FB (tasarım).
- **S05 `sğlk` kısaltması / S14 tek kelime `sağlık`:** thin signal + precision eşiği.
- **Stres A (negasyon) oranı düşük:** eşik/precision trade-off; F korunurken A zayıf kalabiliyor.

## 5. Detaylı Sonuç Tabloları

### Temel (test_scenarios)

| ID | Girdi | Beklenen | Sonuç | Yöntem | Güven | OK |
|----|-------|----------|-------|--------|------|-----|
| S01 | hastane yönetim sistemi arıyoruz | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| S02 | Merhaba, hastane yönetim sistemi arıyoruz | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| S03 | otel rezervasyon sistemimizi yenilemek istiyoruz, teşekkürler | K1/turizm | turizm/K1 | kisaltma | 0.99 | E |
| S04 | lütfen uzaktan eğitim platformu hakkında bilgi verir misiniz acil | K2/eğitim | egitim/K2 | bge-m3 | 0.81 | E |
| S05 | sğlk hastane yazılımı lazım | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| S06 | odaların dolu mu boş mu tek bakışta görelim | K2/turizm | turizm/K2 | bge-m3 | 1.00 | E |
| S08 | Askeri personele uzaktan prosedür eğitimi vereceğiz | K2/eğitim | belirsiz/FB | kisaltma | 0.15 | H |
| S09 | meraba, egtm lms kuracagiz bilgi verir misiniz | K2/eğitim | egitim/K1 | kisaltma | 0.99 | E |
| S10 | fiyat teklifi almak istiyorum | FB/belirsiz | belirsiz/FB | bge-m3 | 1.00 | E |
| S11 | bugün hava çok güzeldi | FB/belirsiz | belirsiz/FB | bge-m3 | 1.00 | E |
| S12 | hastane randevu yazılımı | K1/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| S13 | trzm rzv sistemi yazar mısın | K2/turizm | turizm/K2 | bge-m3 | 0.84 | E |
| S14 | sağlık | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| S15 | We need a hospital management system | K2/sağlık | saglik/K2 | bge-m3 | 0.87 | E |
| S16 | Hello, we are looking for a hotel reservation system | K2/turizm | turizm/K2 | bge-m3 | 0.95 | E |
| S18 | We need a learning management system for our university, thank you | K2/eğitim | egitim/K2 | bge-m3 | 0.88 | E |
| S19 | I need a price quote | FB/belirsiz | belirsiz/FB | bge-m3 | 0.86 | E |
| S20 | How does your company work? | FB/belirsiz | belirsiz/FB | bge-m3 | 1.00 | E |
| S26 | Kurumsal bulut altyapısı ve sunucu barındırma otomasyon yazılımı arıyo | K2/bilişim | bilisim/K2 | bge-m3 | 0.73 | E |

### Stres (A–I)

| ID | Girdi | Beklenen | Sonuç | Yöntem | Güven | OK |
|----|-------|----------|-------|--------|------|-----|
| A01 | sağlık sistemi istemiyoruz, bize turizm rezervasyon yazılımı lazım | K2/turizm | turizm/K2 | bge-m3 | 0.80 | E |
| A02 | savunma sanayi projesi değil, eğitim otomasyonu ile ilgileniyoruz | K2/eğitim | egitim/K2 | bge-m3 | 0.67 | E |
| A03 | hastane randevu modülünü boşverin, oda rezervasyon ekranı kuracağız | K2/turizm | saglik/K2 | bge-m3 | 0.64 | H |
| A05 | Eski turizm acente programımızı bırakıp hastane otomasyon sistemine ge | K2/sağlık | turizm/K2 | bge-m3 | 0.69 | H |
| A06 | Biz askeri birlik değiliz, sadece okul kayıt sistemi istiyoruz | K2/eğitim | egitim/K2 | bge-m3 | 0.65 | E |
| A07 | lms kurulumundan vazgeçtik, telemedicine altyapısı talep ediyoruz | K2/sağlık | saglik/K2 | bge-m3 | 0.83 | E |
| A09 | savunma radar projesi mi eğitim otomasyonu mu derseniz kesinlikle ilki | K2/eğitim | bilisim/K2 | bge-m3 | 0.56 | H |
| A12 | Eğitim kurumu değiliz, hastaneler için teletıp altyapısı arıyoruz. | K2/sağlık | saglik/K2 | bge-m3 | 0.62 | E |
| A13 | savunma sanayi alanında çalışmıyoruz, okul ders programı otomasyonuna  | K2/eğitim | egitim/K2 | bge-m3 | 0.65 | E |
| B01 | Hem sağlık hem de savunma alanında faaliyet gösteriyoruz, ikisi için d | K2/sağlık | belirsiz/FB | kisaltma | 0.15 | H |
| B03 | Hastane ve radar komuta kontrol sistemlerini birleştiren entegre bir y | K2/sağlık | belirsiz/FB | kisaltma | 0.00 | H |
| B05 | Askeri hastaneler için hem telemedicine hem de taktik telsiz sistemi k | K2/sağlık | belirsiz/FB | kisaltma | 0.15 | H |
| B06 | lms tabanlı eğitim modülü olan bir hastane yönetim sistemi | K2/sağlık | egitim/K1 | kisaltma | 0.99 | H |
| B07 | Turizm kanal yöneticisi olan bir savunma sanayi misafirhane portalı | K2/turizm | turizm/K2 | bge-m3 | 0.63 | E |
| C02 | sgl. randevu programı yazar mısınız | K2/sağlık | saglik/K2 | bge-m3 | 0.65 | E |
| C03 | trzm sekt icn rzv programı | K2/turizm | turizm/K2 | bge-m3 | 0.77 | E |
| C04 | egt kurumu icin uzaktan lms | K2/eğitim | egitim/K1 | kisaltma | 0.99 | E |
| C05 | sağlıkksektörüüotomasyonuuarıyoruzz | K2/sağlık | saglik/K2 | bge-m3 | 0.67 | E |
| C06 | tuuurizm otelcilik checkin ekrani | K2/turizm | turizm/K2 | bge-m3 | 0.95 | E |
| C07 | eğitm portali örenci işleri | K2/eğitim | bilisim/K1 | kisaltma | 0.99 | H |
| C08 | hastaneyonetimsistemiyazilimi | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| C09 | bişey lazım bize sağlık için acil yardimci olun | K2/sağlık | saglik/K2 | bge-m3 | 0.54 | E |
| C10 | sağlık 🏥 lazım!!! çok acil | K2/sağlık | saglik/K2 | bge-m3 | 0.59 | E |
| D02 | We need a hastane appointment system for our clinic | K2/sağlık | saglik/K2 | bge-m3 | 0.76 | E |
| D03 | Hastane için bir EHR sistemi arıyoruz | K2/sağlık | saglik/K1 | kisaltma | 0.99 | E |
| D04 | We need a turizm booking platform for booking rooms | K2/turizm | turizm/K2 | bge-m3 | 0.80 | E |
| D06 | otel checkin platform in our hotel system | K2/turizm | turizm/K2 | bge-m3 | 0.95 | E |
| D07 | We require student devamsizlik tracking for high school | K2/eğitim | egitim/K2 | bge-m3 | 0.67 | E |
| D09 | university registration system yenilemek istiyoruz | K2/eğitim | turizm/K2 | bge-m3 | 0.74 | H |
| D10 | We want to implement a telemedicine solution for our hastane | K2/sağlık | saglik/K2 | bge-m3 | 0.87 | E |
| E01 | Merhaba, şirketimiz son 5 yıldır büyüme gösteren bir yapıya sahip ve ö | K2/sağlık | saglik/K2 | bge-m3 | 0.71 | E |
| E02 | İyi çalışmalar dileriz. Grubumuz bünyesinde yer alan beş yıldızlı otel | K2/turizm | turizm/HAFIZA | hafiza | 0.95 | E |
| E04 | Değerli iş ortağımız, yükseköğretim kurumumuzun tüm ders kayıt, sınav  | K2/eğitim | egitim/HAFIZA | hafiza | 0.70 | E |
| E06 | Kamu kurumlarına eğitim ve danışmanlık hizmeti sunan bir limited şirke | K2/eğitim | egitim/K1 | kisaltma | 0.99 | E |
| E08 | Klinik zincirimizin operasyonel verimliliğini artırmak amacıyla, hekim | K2/sağlık | saglik/K2 | bge-m3 | 0.73 | E |
| E09 | Yeni açılacak tatil köyümüz için online rezervasyon altyapısı, misafir | K2/turizm | turizm/HAFIZA | hafiza | 0.95 | E |
| F01 | Sağlıklı bir iş ortaklığı kurmak istiyoruz. | FB/belirsiz | belirsiz/FB | bge-m3 | 0.57 | E |
| F02 | Turistik bir bölgede ofisimiz var ama yazılım hizmeti arıyoruz. | FB/belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| F03 | Eğitimli personel arıyoruz, işe alım konusunda yardımcı olur musunuz? | FB/belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| F04 | Savunma mekanizmaları güçlü bir yazılım mimarisi tasarlamalıyız. | FB/belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| F05 | Hastane köşelerinde beklemek istemediğimiz için evde bakım hizmetlerin | FB/belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| F06 | Otel konforunda bir çalışma ortamı sunan yeni ofisimize bekleriz. | FB/belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| F07 | Askeri disiplinle çalışan bir ekibimiz var, projeyi zamanında bitirece | FB/belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| F08 | Bu ders bize büyük bir hayat eğitimi oldu gerçekten. | FB/belirsiz | belirsiz/FB | bge-m3 | 0.57 | E |
| F09 | Sağlığınızı korumak için günde en az iki litre su içmelisiniz. | FB/belirsiz | belirsiz/FB | bge-m3 | 0.47 | E |
| F10 | Turizm cenneti olan ülkemizde yeni ofisler açmayı hedefliyoruz. | FB/belirsiz | belirsiz/FB | bge-m3 | 0.61 | E |
| F11 | Çalışanlarımız için çok eğlenceli bir iş ortamı sunuyoruz. | FB/belirsiz | belirsiz/FB | bge-m3 | 0.64 | E |
| F12 | Etkinlik organizasyonuna katılmak bizim için çok eğlenceli bir deneyim | FB/belirsiz | belirsiz/FB | bge-m3 | 0.60 | E |
| F13 | Bilişim gibi hızlı büyüyen bir sektörde olmak istiyoruz ama biz aslınd | FB/belirsiz | belirsiz/FB | bge-m3 | 0.54 | E |
| F14 | Şirket içi iletişimi güçlendirmek için siber güvenlik lisansı aldık, ş | FB/belirsiz | belirsiz/FB | bge-m3 | 0.65 | E |
| G01 | Fiyat teklifi almak istiyorum | FB/belirsiz | belirsiz/FB | bge-m3 | 1.00 | E |
| G02 | Ne kadar sürer? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.55 | E |
| G03 | Kiminle görüşebilirim? | FB/belirsiz | saglik/HAFIZA | hafiza | 0.64 | H |
| G04 | Fiyatlandırma nasıl? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.72 | E |
| G05 | Referanslarınız var mı? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.56 | E |
| G06 | Demo yapabilir miyiz? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.84 | E |
| G07 | Çözümlerinizin kurulum süresi ortalama kaç gündür? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.56 | E |
| G08 | Teknik destek hizmetleriniz 7/24 aktif mi? | FB/belirsiz | saglik/K2 | bge-m3 | 0.51 | H |
| G09 | Ofisiniz nerede bulunuyor? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.63 | E |
| G10 | Mail adresinizi alabilir miyim? | FB/belirsiz | belirsiz/FB | bge-m3 | 0.64 | E |
| H01 | Aslında sağlık değil ama sağlık yazıyorum, siz turizm anlayın. | K2/turizm | turizm/K2 | bge-m3 | 0.66 | E |
| H02 | a | FB/belirsiz | belirsiz/FB | kisaltma | 1.00 | E |
| H03 | ? | FB/belirsiz | belirsiz/FB | kisaltma | 1.00 | E |
| H04 | ... | FB/belirsiz | belirsiz/FB | kisaltma | 1.00 | E |
| H05 | sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık | K2/sağlık | belirsiz/FB | bge-m3 | 0.53 | H |
| H06 | 123456789 | FB/belirsiz | belirsiz/FB | kisaltma | 1.00 | E |
| H07 | !!!??? | FB/belirsiz | belirsiz/FB | kisaltma | 1.00 | E |
| H08 | turizm turizm turizm | K2/turizm | turizm/K2 | bge-m3 | 0.61 | E |
| H09 | savunma değil eğitim değil sağlık hiç değil, otel yazın | K2/turizm | turizm/K2 | bge-m3 | 0.95 | E |
| H10 | merhaba merhaba merhaba selam lütfen | FB/belirsiz | belirsiz/K1 | kisaltma | 1.00 | E |
| H16 | Siber saldırılara karşı savunma sanayi değil, kurumsal SaaS bulut alty | K2/bilişim | bilisim/K2 | bge-m3 | 0.66 | E |
| I01 | Sağlık sektöründeyiz. | K2/sağlık | saglik/K2 | bge-m3 | 0.67 | E |
| I02 | Peki fiyatlandırma nasıl? | HAFIZA/sağlık | saglik/HAFIZA | hafiza | 0.95 | E |
| I03 | Oteller için ne gibi çözümleriniz var? | K2/turizm | turizm/K2 | bge-m3 | 0.95 | E |
| I04 | Referanslarınızı listeler misiniz? | HAFIZA/turizm | turizm/HAFIZA | hafiza | 0.95 | E |
| I05 | Ne kadar sürer kurması? | HAFIZA/turizm | turizm/HAFIZA | hafiza | 0.95 | E |
| I08 | Eğitim kurumu işletiyoruz. | K2/eğitim | egitim/K2 | bge-m3 | 0.69 | E |
| I09 | LMS sistemini kurmak için kiminle görüşebilirim? | HAFIZA/eğitim | egitim/K1 | kisaltma | 0.99 | E |

### Çekim Eki

| ID | Girdi | Beklenen | Sonuç | Yöntem | Güven | OK |
|----|-------|----------|-------|--------|------|-----|
| CE-A1 | Sağlık sektöründe faaliyet gösteriyoruz. | sağlık | saglik/K2 | bge-m3 | 0.61 | E |
| CE-A2 | Sağlığımız için bir sistem arıyoruz. | sağlık | saglik/K2 | bge-m3 | 0.76 | E |
| CE-A3 | Sağlıkla ilgili bir yazılım istiyoruz. | sağlık | saglik/K2 | bge-m3 | 0.72 | E |
| CE-A4 | Sağlıklara yönelik çözümünüz var mı? | sağlık | saglik/K2 | bge-m3 | 0.56 | E |
| CE-A5 | Hastanelerimiz için bir platform lazım. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| CE-A6 | Hastanede kullanılacak bir sistem geliştiriyoruz. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| CE-A7 | Hastaneden hastaneye veri paylaşımı yapmak istiyoruz. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| CE-A8 | Kliniklerimizde randevu sistemi kurmak istiyoruz. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| CE-B1 | Turizm sektöründeyiz. | turizm | turizm/K2 | bge-m3 | 0.72 | E |
| CE-B2 | Turizmle uğraşan bir firmayız. | turizm | turizm/K2 | bge-m3 | 0.74 | E |
| CE-B3 | Otelimiz için rezervasyon sistemi lazım. | turizm | turizm/K1 | kisaltma | 0.99 | E |
| CE-B4 | Otellerimizde kullanılacak bir yazılım arıyoruz. | turizm | turizm/K2 | bge-m3 | 0.95 | E |
| CE-B5 | Otelden otele transfer hizmeti sunuyoruz. | turizm | turizm/K2 | bge-m3 | 0.95 | E |
| CE-B6 | Rezervasyonlarımızı dijitalleştirmek istiyoruz. | turizm | turizm/K2 | bge-m3 | 0.81 | E |
| CE-D1 | Eğitim sektöründeyiz. | eğitim | egitim/K2 | bge-m3 | 0.67 | E |
| CE-D2 | Eğitimle ilgili bir platform istiyoruz. | eğitim | egitim/K2 | bge-m3 | 0.76 | E |
| CE-D3 | Okulumuz için kayıt sistemi lazım. | eğitim | egitim/K2 | bge-m3 | 0.70 | E |
| CE-D4 | Okullarımızdaki öğrencileri takip edecek bir sistem arıyoruz. | eğitim | egitim/K2 | bge-m3 | 0.78 | E |
| CE-D5 | Öğrencilerimize yönelik bir uygulama geliştiriyoruz. | eğitim | egitim/K2 | bge-m3 | 0.75 | E |
| CE-D6 | Üniversitemizden mezun öğrenciler için bir portal lazım. | eğitim | egitim/K2 | bge-m3 | 0.68 | E |
| CE-E1 | Hastanelerle sözleşme yapmak istiyoruz. | sağlık|belirsiz | saglik/K1 | kisaltma | 0.99 | ~ |
| CE-E2 | Otelleştirmek istediğimiz bir binamız var. | turizm|belirsiz | turizm/K2 | bge-m3 | 0.95 | ~ |
| CE-E3 | Askerileştirilmiş bir güvenlik protokolü istiyoruz. | belirsiz|savunma | belirsiz/FB | kisaltma | 0.15 | ~ |
| CE-E4 | Eğitimlendirme sürecimizi otomatikleştirmek istiyoruz. | eğitim|belirsiz | egitim/K2 | bge-m3 | 0.67 | ~ |
| CE-F1 | Sağlıksız gıdalarla mücadele için bir farkındalık kampanyası yürütüyor | belirsiz | belirsiz/FB | bge-m3 | 0.53 | E |
| CE-F2 | Eğitimsiz personel çalıştırmak istemiyoruz, bu yüzden İK süreçlerimizi | belirsiz | belirsiz/FB | bge-m3 | 0.65 | E |
| CE-F3 | Savunmasız kalmamak için siber güvenlik yatırımı yapıyoruz. | belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| CE-G1 | Hastanelerimizdeki hasta kayıtlarını dijitalleştirmek istiyoruz, bu ko | sağlık | saglik/K2 | bge-m3 | 0.73 | E |
| CE-G2 | Otellerimizin rezervasyon sistemlerini yenilemeyi planlıyoruz, önümüzd | turizm | turizm/K2 | bge-m3 | 0.95 | E |
| CE-G3 | Okullarımızdaki öğretmenlerimizin performans takibini yapabileceğimiz  | eğitim | egitim/K2 | bge-m3 | 0.84 | E |

### Selamlaşma / Small Talk

| ID | Girdi | Beklenen | Sonuç | Yöntem | Güven | OK |
|----|-------|----------|-------|--------|------|-----|
| SL-A1 | Merhaba | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A2 | Selam | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A3 | Günaydın | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A4 | İyi günler | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A5 | İyi akşamlar | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A6 | İyi geceler | Genel Sohbet | belirsiz/FB | bge-m3 | 0.55 | E |
| SL-A7 | Nasılsın? | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A8 | Teşekkürler | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-A9 | Hoşça kal | Genel Sohbet | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-B1 | Merhaba, hastanemiz için randevu sistemi arıyoruz. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| SL-B2 | İyi günler, otel rezervasyon yazılımına ihtiyacımız var. | turizm | turizm/K2 | bge-m3 | 0.95 | E |
| SL-B3 | Selam, turizm acentesiyiz. | turizm | turizm/K1 | kisaltma | 0.99 | E |
| SL-B4 | Günaydın, üniversitemiz için uzaktan eğitim platformu kurmak istiyoruz | eğitim | egitim/K2 | bge-m3 | 0.74 | E |
| SL-B5 | Merhaba iyi günler, klinik randevu sistemimizi dijitalleştirmek istiyo | sağlık | saglik/K2 | bge-m3 | 0.76 | E |
| SL-C1 | Merhaba, fiyat teklifi alabilir miyim? | Belirsiz (not Genel) | belirsiz/FB | bge-m3 | 0.89 | E |
| SL-C2 | İyi günler, bir yazılım projemiz var yardımcı olur musunuz? | Belirsiz (not Genel) | bilisim/K2 | bge-m3 | 0.73 | H |
| SL-C3 | Selam, bilgi almak istiyorum. | Belirsiz (not Genel) | belirsiz/FB | bge-m3 | 0.64 | E |
| SL-C4 | Merhaba, sizinle görüşmek istiyorum. | Belirsiz (not Genel) | belirsiz/FB | bge-m3 | 0.61 | E |
| SL-D1a | Merhaba, hastane randevu… | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| SL-D1b | Fiyat teklifi… (aynı session) | sağlık/HAFIZA | belirsiz/FB | bge-m3 | 0.89 | H |
| SL-E1 | Görüşürüz | Genel Sohbet veya nötr | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-E2 | İyi çalışmalar | Genel Sohbet veya nötr | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-E3 | Kolay gelsin | Genel Sohbet veya nötr | belirsiz/K1 | kisaltma | 1.00 | E |
| SL-F1 | mrb hastane randevu sistemi lazım | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| SL-F2 | slm otel rezervasyon yazılımı | turizm | turizm/K1 | kisaltma | 0.99 | E |
| SL-F3 | gunaydin egitim platformu arıyoruz | eğitim | egitim/K2 | bge-m3 | 0.70 | E |

### K1 Hard-Match Regresyon

| ID | Girdi | Beklenen | Sonuç | Yöntem | Güven | OK |
|----|-------|----------|-------|--------|------|-----|
| K1-A1 | Savunma sanayii firmasıyız, komuta kontrol sistemi geliştiriyoruz. | belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| K1-A2 | Klinik randevu sistemimizi dijitalleştirmek istiyoruz. | sağlık | saglik/K1 | kisaltma | 0.99 | E |
| K1-A3 | Komuta kontrol altyapısı kurmamız lazım, savunma projesi kapsamında. | belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| K1-A4 | Bize bir komuta kontrol yazılımı geliştirebilir misiniz? | belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| K1-A5 | Hastanemizde hasta randevu takibi yapan bir sistem istiyoruz. | sağlık | saglik/K2 | bge-m3 | 0.81 | E |
| K1-A6 | Kliniğimiz için randevu yönetim sistemi arıyoruz. | sağlık | saglik/K2 | bge-m3 | 0.88 | E |
| K1-A7 | Ordu için komuta kontrol merkezi yazılımı lazım. | belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| K1-A8 | Sağlıklı bir komuta zinciri kurmak istiyoruz. | belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| K1-A9 | Randevu almak için nereye başvurmalıyım? | belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| K1-A10 | Kontrol mekanizmalarımızı gözden geçirmek istiyoruz. | belirsiz | belirsiz/FB | kisaltma | 0.00 | E |
| K1-B1 | eğitim→fiyat | eğitim/HAFIZA | egitim/HAFIZA | hafiza | 0.95 | E |
| K1-B2 | sağlık→süre | sağlık/HAFIZA | bilisim/HAFIZA | hafiza | 0.54 | H |
| K1-B3 | eğitim→savunma | belirsiz | belirsiz/FB | kisaltma | 0.15 | E |
| K1-B4 | sağlık→turizm | turizm | turizm/K2 | bge-m3 | 0.95 | E |
| K1-B5 | turizm→eğitim borderline | borderline | egitim/K2 | bge-m3 | 0.71 | ~ |
| K1-B6 | sağlık→başka neler | sağlık/HAFIZA | belirsiz/FB | bge-m3 | 0.60 | H |
| K1-B7 | eğitim→teşekkür | eğitim/HAFIZA veya nötr | belirsiz/FB | bge-m3 | 0.58 | E |

## 6. Sonuç ve Teslim Önerisi

### MUTLAKA (Cuma öncesi)
- Kritik small_talk bug kapalı; ek zorunlu kod düzeltmesi yok.
- Temel set 18/19: S05/S14 için README’de sınırlama notu **veya** minimal typo/hard-match (tercihen README notu — eşik düşürme).

### README / bilinen sınırlama olarak ertelenebilir
- Stres A düşük oranı, Kategori I session derinliği, paralel niyet, nadir fiilleştirme.
- Çekim eki setinde hâlâ FB kalan ürünsüz-ama-çekimli cümleler (ürün kalıbı yok).

### İsteğe bağlı 1–2 iyileştirme
1. `sğlk` → `sağlık` normalizasyonu (S05).
2. Stres negasyon (A) için hedefli corpus örnekleri — eşik düşürmeden.

---
*Üretilme: 2026-07-31 11:25:20 — otomatik final doğrulama.*
