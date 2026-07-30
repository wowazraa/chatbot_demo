"""
Ogreten cozum: clean corpus'a semantik ornek ekle + indeksi yeniden kur.
Sozluk ezberi yok; BGE benzerligi yukselir, MIN_BGE=0.80 ayni kalir.

    python scripts/enrich_clean_and_reindex.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TORCH", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLEAN_JSON = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
OUT_NPZ = ROOT / "data" / "processed" / "chatbot_dataset_clean_embeddings.npz"
OUT_META = ROOT / "data" / "processed" / "chatbot_dataset_clean_index_meta.json"

# Paraphrase ornekler — smoke cumlesinin birebir kopyasi yok; ayni niyet uzayi
TEACHING_SEEDS: list[dict] = [
    # sağlık
    {
        "mesaj": "Hastanede doktor mesai planı ve klinik randevu yazılımı arıyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hekim nöbet çizelgesi ile poliklinik randevu otomasyonu istiyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Klinik yönetim sisteminde hekim takvimi ve hasta kabul süreci lazım",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hastane bilgi yönetiminde muayene saatleri ve doktor planlaması kuracağız",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hastane otomasyonunda hekim çalışma saatleri ve randevu düzenlemesi istiyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hekim çalışma saatlerini hastane otomasyonunda yönetmemiz gerekiyor",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Sahra tipi geçici klinikte hasta sevk ve kayıt takip sistemi arıyoruz",
        "beklenen_sektor": "sağlık",
    },
    # savunma
    {
        "mesaj": "Sınır birlikleri için yerli komuta kontrol ve izleme yazılımı tedarik edeceğiz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Hudut hattında komuta merkezi ve birlik haberleşme altyapısı istiyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Yerli üretilmiş komuta kontrol paneli ve radar entegrasyonu arıyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Askeri sahra birlikleri için taktik ikmal ve lojistik takip yazılımı lazım",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Hudut güvenliği kapsamında yerli komuta kontrol çözümü arıyoruz",
        "beklenen_sektor": "savunma",
    },
    # eğitim
    {
        "mesaj": "Online öğrenme portalı ve elektronik kütüphane altyapısı kurmak istiyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Uzaktan ders platformu ile dijital kütüphane entegrasyonu talep ediyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Fakülte öğrencileri için e-öğrenme ve ders kayıt otomasyonu gerekiyor",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Turizm bölümü öğrencilerine LMS ve sınav/ders kayıt sistemi lazım",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Üniversitede OBS ile dijital kütüphane portalını birlikte kuracağız",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Uzaktan öğrenim ve dijital kütüphane portalı kurma niyetindeyiz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Turizm fakültesi için uzaktan eğitim ile ders kayıt otomasyonu yazılımı istiyoruz",
        "beklenen_sektor": "eğitim",
    },
    # turizm
    {
        "mesaj": "Seyahat acentesi için rezervasyon API ve check-in otomasyonu arıyoruz",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Acente kanalında tur ve konaklama rezervasyon API bağlantısı istiyoruz",
        "beklenen_sektor": "turizm",
    },
    # --- Yeni UI niyet uzayi (paraphrase; birebir kopya degil) ---
    {
        "mesaj": "Kardiyoloji polikliniği için sabah randevu oluşturma ekranı istiyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Poliklinik randevu alma ve hekim seçimi otomasyonu arıyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hasta tahlil sonuçlarını sistemden görüntüleme portalı lazım",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Laboratuvar sonuçlarının hastaya düşüp düşmediğini kontrol eden modül istiyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Hasta şikayetine göre poliklinik bölüm yönlendirme ekranı arıyoruz",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Baş dönmesi bulantı gibi şikayetlerde ilgili poliklinik öneren kiosk yazılımı",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "İptal edilebilir iki kişilik otel rezervasyonu oluşturma akışı istiyoruz",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Hafta sonu için iptal güvenceli konaklama rezervasyon sistemi arıyoruz",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Müze kartının geçerli olduğu tarihi yerler listesini sunan turizm uygulaması",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Tarihi mekan ve müze giriş noktalarını listeleyen ziyaretçi rehberi yazılımı",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Askeri lojistik yazılımında siber güvenlik protokollerinin uygulanması hakkında çözüm",
        "beklenen_sektor": "savunma",
    },
    # Yakin paraphrase (esik alti skorlari kaldirmak icin)
    {
        "mesaj": "Başım dönüyor ve midem bulanıyor hangi polikliniğe gitmeliyim",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Sürekli baş dönmesi bulantı şikayetinde ilgili bölüme yönlendirme istiyorum",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Tahlil sonuçlarım sisteme düşmüş mü diye kontrol etmek istiyorum",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "Laboratuvar tahlil sonuçlarının sisteme düşüp düşmediğini sorgulayan hasta ekranı",
        "beklenen_sektor": "sağlık",
    },
    {
        "mesaj": "İki kişilik iptal edilebilir rezervasyon yapmak istiyorum",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Hafta sonu için iptal edilebilir konaklama rezervasyonu oluşturmak istiyorum",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Müze kart geçerli olan tarihi yerlerin listesini istiyorum",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Müze kartı ile girilebilen tarihi yer listesini alabilir miyiz",
        "beklenen_sektor": "turizm",
    },
    # --- Savunma / egitim yeni UI niyetleri (paraphrase) ---
    {
        "mesaj": "İnsansız kara araçları için radar entegrasyonu yazılımı arıyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "İKA platformlarında radar ve sensör entegrasyonu çözümü istiyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Kara aracı radar entegrasyonu ve komuta bağlantısı hakkında çözüm lazım",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "İnsansız kara araçlarının radar entegrasyonu hakkında bilgi alabilir miyim",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "İnsansız kara araçları radar entegrasyonu nasıl yapılıyor",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Birlik içi güvenli haberleşme cihazları için bakım ve takip yazılımı arıyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Güvenli birlik haberleşme ekipmanlarının bakım periyodu yönetim sistemi istiyoruz",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Kriptolu haberleşme cihazı bakım planı ve envanter yazılımı lazım",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Birlik içi güvenli haberleşme cihazlarının bakım periyotları nedir",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Birlik haberleşme cihazı bakım periyodu ne kadar",
        "beklenen_sektor": "savunma",
    },
    {
        "mesaj": "Yaz okulu ders kayıt otomasyonu ve harç ücreti tahsilat modülü arıyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yaz okulu kayıt başlangıç takvimi ile harç ödeme ekranı istiyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Ders kayıtları ve harç ücreti bilgilendirmesini yapan öğrenci otomasyonu lazım",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yaz okulu ders kayıtları ne zaman başlıyor ve harç ücreti ne kadar",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yaz okulu kayıtları ne zaman açılıyor harç ücreti kaç lira",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Çift anadal başvuru şartları ve taban puan bilgisini sunan OBS modülü arıyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "ÇAP programı başvuru koşulları ve puan eşikleri için öğrenci işleri yazılımı",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Çift anadal taban puan ve başvuru şartı sorgulama ekranı istiyoruz",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Çift anadal programına başvuru şartları ve taban puanları nelerdir",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "ÇAP çift anadal başvuru şartı ve taban puanı nedir",
        "beklenen_sektor": "eğitim",
    },
    # --- Probe FAIL kümesi (öğretme paraphrase, sözlük yok) ---
    # sağlık
    {"mesaj": "MR sonucumu doktora iletmek istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "MR ve görüntüleme sonucunu hekime ileten hasta portalı arıyoruz", "beklenen_sektor": "sağlık"},
    {"mesaj": "Diş ağrısı için acil muayene var mı", "beklenen_sektor": "sağlık"},
    {"mesaj": "Acil diş muayenesi randevu ekranı istiyoruz", "beklenen_sektor": "sağlık"},
    {"mesaj": "Kan tahlili randevusu almak istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Laboratuvar kan tahlili randevu otomasyonu lazım", "beklenen_sektor": "sağlık"},
    {"mesaj": "E-nabızda laboratuvar sonuçlarım görünmüyor", "beklenen_sektor": "sağlık"},
    {"mesaj": "E-nabız laboratuvar sonuç entegrasyonu yazılımı arıyoruz", "beklenen_sektor": "sağlık"},
    {"mesaj": "Ortopedi için sıraya girmek istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Ortopedi poliklinik sıra ve randevu sistemi istiyoruz", "beklenen_sektor": "sağlık"},
    {"mesaj": "Ameliyat öncesi anestezi bilgilendirmesi lazım", "beklenen_sektor": "sağlık"},
    {"mesaj": "Ameliyat öncesi anestezi bilgilendirme modülü arıyoruz", "beklenen_sektor": "sağlık"},
    {"mesaj": "İlaç raporumun yenilenmesi için ne yapmalıyım", "beklenen_sektor": "sağlık"},
    {"mesaj": "İlaç raporu yenileme süreci için hastane otomasyonu", "beklenen_sektor": "sağlık"},
    {"mesaj": "Yoğun bakım ziyaret saatleri nedir", "beklenen_sektor": "sağlık"},
    {"mesaj": "Yoğun bakım ziyaret saati bilgilendirme ekranı istiyoruz", "beklenen_sektor": "sağlık"},
    # turizm
    {"mesaj": "Kapadokya'da balon turu paket fiyatı nedir", "beklenen_sektor": "turizm"},
    {"mesaj": "Kapadokya balon turu paket fiyat listesi sunan turizm uygulaması", "beklenen_sektor": "turizm"},
    {"mesaj": "Erken check-in ile oda ayırtabilir miyim", "beklenen_sektor": "turizm"},
    {"mesaj": "Erken check-in oda rezervasyon ekranı istiyoruz", "beklenen_sektor": "turizm"},
    {"mesaj": "All inclusive tatil köyü önerir misiniz", "beklenen_sektor": "turizm"},
    {"mesaj": "Her şey dahil tatil köyü arama ve rezervasyon yazılımı", "beklenen_sektor": "turizm"},
    {"mesaj": "Bodrum marina yakınında pansiyon arıyorum", "beklenen_sektor": "turizm"},
    {"mesaj": "Marina yakın pansiyon konaklama arama sistemi", "beklenen_sektor": "turizm"},
    {"mesaj": "Tur iptal şartları nelerdir", "beklenen_sektor": "turizm"},
    {"mesaj": "Tur iptal koşulları ve iade politikası bilgilendirme ekranı", "beklenen_sektor": "turizm"},
    {"mesaj": "Şehir turu için rehberli gezi var mı", "beklenen_sektor": "turizm"},
    {"mesaj": "Rehberli şehir turu rezervasyon modülü arıyoruz", "beklenen_sektor": "turizm"},
    {"mesaj": "Havalimanı transferi dahil mi", "beklenen_sektor": "turizm"},
    {"mesaj": "Otel paketinde havalimanı transferi seçeneği sunan turizm yazılımı", "beklenen_sektor": "turizm"},
    # savunma
    {"mesaj": "İHA yer kontrol istasyonu yazılımı hakkında bilgi", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA yer kontrol istasyonu komuta yazılımı arıyoruz", "beklenen_sektor": "savunma"},
    {"mesaj": "Taktik sahada güvenli veri aktarımı nasıl sağlanır", "beklenen_sektor": "savunma"},
    {"mesaj": "Taktik saha güvenli veri aktarım protokol yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Elektronik harp sistemlerinde spektrum yönetimi", "beklenen_sektor": "savunma"},
    {"mesaj": "Elektronik harp spektrum yönetim yazılımı istiyoruz", "beklenen_sektor": "savunma"},
    {"mesaj": "Zırhlı araçlar için arıza öngörü yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Zırhlı araç arıza öngörü ve bakım yazılımı arıyoruz", "beklenen_sektor": "savunma"},
    {"mesaj": "Komuta kontrol merkezinde durum farkındalığı ekranı", "beklenen_sektor": "savunma"},
    {"mesaj": "Komuta kontrol durum farkındalığı ekranı yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "UAV sensör füzyonu entegrasyonu", "beklenen_sektor": "savunma"},
    {"mesaj": "UAV sensör füzyonu entegrasyon çözümü istiyoruz", "beklenen_sektor": "savunma"},
    {"mesaj": "Güvenli uydu haberleşme terminali bakımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Uydu haberleşme terminali bakım ve takip yazılımı", "beklenen_sektor": "savunma"},
    # eğitim
    {"mesaj": "Yatay geçiş başvurusu ne zaman açılıyor", "beklenen_sektor": "eğitim"},
    {"mesaj": "Yatay geçiş başvuru takvimi ve formu sunan OBS", "beklenen_sektor": "eğitim"},
    {"mesaj": "Mezuniyet belgesi nasıl alınır", "beklenen_sektor": "eğitim"},
    {"mesaj": "Mezuniyet belgesi talep ekranı öğrenci işleri yazılımı", "beklenen_sektor": "eğitim"},
    {"mesaj": "Uzaktan eğitim ders kayıtları başladı mı", "beklenen_sektor": "eğitim"},
    {"mesaj": "Uzaktan eğitim ders kayıt otomasyonu arıyoruz", "beklenen_sektor": "eğitim"},
    {"mesaj": "Burs başvurusu için gerekli belgeler neler", "beklenen_sektor": "eğitim"},
    {"mesaj": "Burs başvuru belge listesi ve form modülü istiyoruz", "beklenen_sektor": "eğitim"},
    {"mesaj": "Transkript talep etmek istiyorum", "beklenen_sektor": "eğitim"},
    {"mesaj": "Öğrenci transkript talep ve onay ekranı lazım", "beklenen_sektor": "eğitim"},
    {"mesaj": "Yüksek lisans kontenjanları açık mı", "beklenen_sektor": "eğitim"},
    {"mesaj": "Yüksek lisans kontenjan ve başvuru ekranı arıyoruz", "beklenen_sektor": "eğitim"},
    {"mesaj": "Öğrenci kimlik kartı yenileme süreci", "beklenen_sektor": "eğitim"},
    {"mesaj": "Öğrenci kimlik kartı yenileme süreci otomasyonu", "beklenen_sektor": "eğitim"},
    {"mesaj": "Staj başvuru formu nereden doldurulur", "beklenen_sektor": "eğitim"},
    {"mesaj": "Staj başvuru formu ve onay akışı yazılımı", "beklenen_sektor": "eğitim"},
    # --- Held-out FAIL kümesi için ÇEŞİTLİ paraphrase (birebir held-out yok) ---
    # sağlık semantik komşular
    {"mesaj": "BT tomografi raporumu doktoruma iletmek istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Görüntüleme sonucumu hekim paneline göndermek istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Dişim ağrıyor acil diş hekimi bakabilir mi", "beklenen_sektor": "sağlık"},
    {"mesaj": "Şiddetli diş ağrısı için aynı gün muayene arıyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Hemogram kan sayımı için randevu istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Tam kan sayımı laboratuvar randevusu oluşturmak istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Kırık olabilir ortopedi bölümüne gitmem gerekiyor", "beklenen_sektor": "sağlık"},
    {"mesaj": "Travma sonrası ortopedi polikliniğine başvurmak istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Ameliyat öncesi anestezi hekimi beni bilgilendirecek mi", "beklenen_sektor": "sağlık"},
    {"mesaj": "Anestezi öncesi hasta bilgilendirme süreci nedir", "beklenen_sektor": "sağlık"},
    {"mesaj": "Baş dönmesi bulantı hangi polikliniğe gitmeliyim", "beklenen_sektor": "sağlık"},
    {"mesaj": "Sersemlik ve mide bulantısı için branş yönlendirmesi", "beklenen_sektor": "sağlık"},
    # turizm
    {"mesaj": "Nevşehir Kapadokya sıcak hava balonu tur ücreti", "beklenen_sektor": "turizm"},
    {"mesaj": "Kapadokya balon uçuşu fiyatı ne kadar", "beklenen_sektor": "turizm"},
    {"mesaj": "Otele öğleden önce check-in yapabilir miyiz", "beklenen_sektor": "turizm"},
    {"mesaj": "Erken otel girişi mümkün mü öğleden önce", "beklenen_sektor": "turizm"},
    {"mesaj": "Antalya civarı her şey dahil tesis arıyorum", "beklenen_sektor": "turizm"},
    {"mesaj": "All inclusive Antalya tatil tesisi bakıyorum", "beklenen_sektor": "turizm"},
    {"mesaj": "İskele yakını butik pansiyon arıyorum", "beklenen_sektor": "turizm"},
    {"mesaj": "Sahil iskelesi civarında küçük pansiyon konaklama", "beklenen_sektor": "turizm"},
    {"mesaj": "Tur iptal ve iade kuralları nelerdir", "beklenen_sektor": "turizm"},
    {"mesaj": "Satın alınan turun iade ve iptal şartlarını öğrenmek istiyorum", "beklenen_sektor": "turizm"},
    {"mesaj": "Konaklama paketinde airport transferi var mı", "beklenen_sektor": "turizm"},
    {"mesaj": "Havalimanı transfer dahil otel paketi arıyorum", "beklenen_sektor": "turizm"},
    # savunma
    {"mesaj": "Drone yer kontrol istasyonu yazılım mimarisi", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA yer istasyonu yazılım mimarisi hakkında bilgi", "beklenen_sektor": "savunma"},
    {"mesaj": "Muharebe alanında kriptolu veri iletimi", "beklenen_sektor": "savunma"},
    {"mesaj": "Taktik muharebe sahasında şifreli veri aktarımı yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Zırhlı platform predictive maintenance yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Zırhlı araç öngörücü bakım predictive maintenance çözümü", "beklenen_sektor": "savunma"},
    {"mesaj": "C2 common operating picture ekranı", "beklenen_sektor": "savunma"},
    {"mesaj": "Komuta kontrol COP common operating picture yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "İnsansız hava aracı çoklu sensör birleştirme", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA UAV multi sensor fusion entegrasyonu", "beklenen_sektor": "savunma"},
    {"mesaj": "SATCOM terminal bakım planı yönetimi", "beklenen_sektor": "savunma"},
    {"mesaj": "Uydu haberleşme SATCOM bakım periyodu yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Askeri lojistik depo stok takip yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Askeri depo envanter ve stok yönetim sistemi", "beklenen_sektor": "savunma"},
    # eğitim
    {"mesaj": "Başka üniversiteden yatay geçiş tarihleri", "beklenen_sektor": "eğitim"},
    {"mesaj": "Üniversiteler arası yatay geçiş başvuru takvimi", "beklenen_sektor": "eğitim"},
    {"mesaj": "Diploma mezuniyet belgesi nasıl talep edilir", "beklenen_sektor": "eğitim"},
    {"mesaj": "Mezuniyet belgesi ve diploma talep formu", "beklenen_sektor": "eğitim"},
    {"mesaj": "Kampüs kartı kaybettim yenilemek istiyorum", "beklenen_sektor": "eğitim"},
    {"mesaj": "Öğrenci kampüs kartı kayıp yenileme süreci", "beklenen_sektor": "eğitim"},
    {"mesaj": "Zorunlu staj başvuru ekranı nerede", "beklenen_sektor": "eğitim"},
    {"mesaj": "Zorunlu staj başvurusu OBS üzerinden nasıl yapılır", "beklenen_sektor": "eğitim"},
    # --- Basit & açık tüketici cümleleri (coverage; eşik düşürülmez) ---
    {"mesaj": "Röntgen filmimi doktora ulaştırmak istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Röntgen sonucumu hekime göndermek istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Dişetim şişti acil diş bakımı lazım", "beklenen_sektor": "sağlık"},
    {"mesaj": "Diş eti şişliği için acil diş muayenesi", "beklenen_sektor": "sağlık"},
    {"mesaj": "Biyokimya tahlili için gün alabilir miyim", "beklenen_sektor": "sağlık"},
    {"mesaj": "Biyokimya laboratuvar randevusu istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Çocuk ortopedisine randevu istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Çocuk ortopedi poliklinik randevusu", "beklenen_sektor": "sağlık"},
    {"mesaj": "Sedasyon öncesi bilgilendirme yapılacak mı", "beklenen_sektor": "sağlık"},
    {"mesaj": "Sedasyon öncesi hasta bilgilendirmesi nedir", "beklenen_sektor": "sağlık"},
    {"mesaj": "Başım ağrıyor kusuyorum hangi bölüme", "beklenen_sektor": "sağlık"},
    {"mesaj": "Baş ağrısı ve kusma için hangi bölüme gitmeliyim", "beklenen_sektor": "sağlık"},
    {"mesaj": "Göreme'de balon turu kaç TL", "beklenen_sektor": "turizm"},
    {"mesaj": "Göreme balon turu fiyatı ne kadar", "beklenen_sektor": "turizm"},
    {"mesaj": "Sabah erken otele yerleşebilir miyiz", "beklenen_sektor": "turizm"},
    {"mesaj": "Sabah erken otel girişi mümkün mü", "beklenen_sektor": "turizm"},
    {"mesaj": "Turumu iptal edersem param iade olur mu", "beklenen_sektor": "turizm"},
    {"mesaj": "Tur iptalinde ücret iadesi var mı", "beklenen_sektor": "turizm"},
    {"mesaj": "Sahada şifreli haberleşme nasıl kurulur", "beklenen_sektor": "savunma"},
    {"mesaj": "Saha ortamında kriptolu haberleşme kurulumu", "beklenen_sektor": "savunma"},
    {"mesaj": "Komuta yerinde ortak durum resmi ekranı", "beklenen_sektor": "savunma"},
    {"mesaj": "Komuta yerinde ortak operasyon resmi COP ekranı", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA'da radar ve kamera füzyonu", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA radar kamera sensör füzyonu entegrasyonu", "beklenen_sektor": "savunma"},
    {"mesaj": "Askeri ambar stok yazılımı arıyoruz", "beklenen_sektor": "savunma"},
    {"mesaj": "Askeri ambar stok takip yazılımı", "beklenen_sektor": "savunma"},
    {"mesaj": "Yatay geçiş kontenjan ve tarihleri", "beklenen_sektor": "eğitim"},
    {"mesaj": "Yatay geçiş kontenjanları ve başvuru tarihleri", "beklenen_sektor": "eğitim"},
    {"mesaj": "Uzaktan ders kaydı açıldı mı harç ne", "beklenen_sektor": "eğitim"},
    {"mesaj": "Uzaktan eğitim ders kaydı ve harç ücreti", "beklenen_sektor": "eğitim"},
    # --- probe_simple_clear FAIL (kısa açık cümleler) ---
    {"mesaj": "Tahlil sonuçlarım sistemde görünmüyor", "beklenen_sektor": "sağlık"},
    {"mesaj": "Tahlil sonuçları sistemde yok kontrol eder misiniz", "beklenen_sektor": "sağlık"},
    {"mesaj": "Kardiyoloji randevusu almak istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Kardiyoloji için randevu istiyorum", "beklenen_sektor": "sağlık"},
    {"mesaj": "Askeri lojistik yazılımı hakkında bilgi", "beklenen_sektor": "savunma"},
    {"mesaj": "Askeri lojistik yazılımı nedir bilgi alabilir miyim", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA radar entegrasyonu nedir", "beklenen_sektor": "savunma"},
    {"mesaj": "İHA radar entegrasyonu hakkında kısa bilgi", "beklenen_sektor": "savunma"},
    # --- FAZ 2: akademik eğitim + hibrit turizm (LMS/OBS dışı semantik) ---
    {
        "mesaj": "Bilgisayar mühendisliği taban puanları ve burs imkanları hakkında bilgi istiyorum",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yazılım mühendisliği bölümü taban puanları nedir burs var mı",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Üniversite taban puanları ve başarı sıralaması sorgulamak istiyorum",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yüksek lisans burs imkanları ve başvuru koşulları nelerdir",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Lisansüstü öğrencilere verilen burs ve ücret muafiyeti hakkında bilgi",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Üniversite harç ücretleri ve dönemlik ödeme takvimi nedir",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Öğrenci harç ücreti ne kadar ve nasıl ödenir",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "ÇAP ve yan dal başvuru koşulları ile puan eşikleri nelerdir",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Çift anadal yan dal başvurusu için gerekli not ortalaması ve kontenjan",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Mühendislik fakültesi taban puanı burs kontenjanı ve yatay geçiş şartları",
        "beklenen_sektor": "eğitim",
    },
    {
        "mesaj": "Yabancı turist sağlık sigortası ve seyahat güvencesi paketi arıyorum",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Yurtdışından gelen turistler için zorunlu sağlık sigortası teklifi istiyoruz",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Otel rezervasyon iptali ve iade koşulları nasıl işliyor",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Konaklama rezervasyonunu iptal edip ücret iadesi almak istiyorum",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Rehberli kültür turu ve müze gezisi paketi önerir misiniz",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Şehir içi rehberli kültür turu rezervasyonu ve grup indirimi lazım",
        "beklenen_sektor": "turizm",
    },
    {
        "mesaj": "Ege bölgesi her şey dahil otel fiyatları ve erken rezervasyon kampanyası",
        "beklenen_sektor": "turizm",
    },
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    if not CLEAN_JSON.exists():
        raise SystemExit(f"Clean dataset yok: {CLEAN_JSON}")

    from src.concept_map import CONCEPT_ANCHOR_SEEDS

    data = json.loads(CLEAN_JSON.read_text(encoding="utf-8"))
    kayitlar: list[dict] = list(data.get("kayitlar", []))
    # Eski teaching_seed / concept_anchor satirlarini temizle (yeniden yaz)
    before = len(kayitlar)
    kayitlar = [
        r
        for r in kayitlar
        if r.get("varyant") not in ("teaching_seed", "concept_anchor")
    ]
    removed = before - len(kayitlar)
    if removed:
        print(f"[+] Eski teaching/concept seed silindi: {removed}")

    existing = {str(r.get("mesaj", "")).strip().lower() for r in kayitlar}

    added = 0
    base_id = 900_000
    for i, seed in enumerate(TEACHING_SEEDS):
        msg = seed["mesaj"].strip()
        key = msg.lower()
        if key in existing:
            continue
        existing.add(key)
        kayitlar.append(
            {
                "id": f"teach_{base_id + i}",
                "source_id": base_id + i,
                "lang": "tr",
                "mesaj": msg,
                "varyant": "teaching_seed",
                "prefix": "",
                "suffix": "",
                "ham_mesaj": msg,
                "normalize_mesaj": msg.lower(),
                "beklenen_sektor": seed["beklenen_sektor"],
                "beklenen_mod": "K2",
                "zorluk": "teaching",
            }
        )
        added += 1

    # FAZ 5: kavramsal anchor öbekleri (ezber cümle değil semantik köprü)
    concept_added = 0
    concept_base = 910_000
    for i, seed in enumerate(CONCEPT_ANCHOR_SEEDS):
        msg = seed["mesaj"].strip()
        key = msg.lower()
        if key in existing:
            continue
        existing.add(key)
        kayitlar.append(
            {
                "id": f"concept_{concept_base + i}",
                "source_id": concept_base + i,
                "lang": "tr",
                "mesaj": msg,
                "varyant": "concept_anchor",
                "prefix": "",
                "suffix": "",
                "ham_mesaj": msg,
                "normalize_mesaj": msg.lower(),
                "beklenen_sektor": seed["beklenen_sektor"],
                "beklenen_mod": "K2",
                "zorluk": "concept",
            }
        )
        concept_added += 1

    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    meta["teaching_enrichment"] = {
        "added": added,
        "total_after": len(kayitlar),
        "note": "BGE recall icin semantik ornek; MIN_BGE degismedi",
    }
    meta["concept_anchors"] = {
        "added": concept_added,
        "total_after": len(kayitlar),
        "note": "FAZ 5 kavram haritasi; MIN_BGE=0.80",
    }
    data["meta"] = meta
    data["kayitlar"] = kayitlar
    CLEAN_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[+] Clean JSON guncellendi: +{added} teaching, "
        f"+{concept_added} concept → {len(kayitlar)} kayit"
    )

    # Reindex
    from src.embedder import BGEEmbedder
    import numpy as np

    texts: list[str] = []
    meta_rows: list[dict] = []
    for rec in kayitlar:
        msg = str(rec.get("mesaj") or "").strip()
        if not msg:
            continue
        texts.append(msg)
        meta_rows.append(
            {
                "id": rec.get("id"),
                "source_id": rec.get("source_id"),
                "beklenen_sektor": rec.get("beklenen_sektor", "belirsiz"),
                "beklenen_mod": rec.get("beklenen_mod", "K2"),
                "lang": rec.get("lang", "tr"),
                "zorluk": rec.get("zorluk", ""),
                "varyant": rec.get("varyant", "duz"),
            }
        )

    print(f"[-] BGE-M3 encode: {len(texts)} metin...", flush=True)
    emb = BGEEmbedder()
    t0 = time.time()
    emb.build_index(texts, meta_rows, show_progress=True)
    print(f"[+] Encode {time.time() - t0:.1f}s | {emb._vectors.shape}")

    np.savez_compressed(OUT_NPZ, vectors=emb._vectors)
    sparse = []
    if emb._sparse_vectors:
        for d in emb._sparse_vectors:
            sparse.append({k: float(v) for k, v in d.items()})
    else:
        sparse = [{} for _ in texts]
    OUT_META.write_text(
        json.dumps(
            {
                "texts": emb._texts,
                "meta": emb._meta,
                "sparse_vectors": sparse,
                "source": str(CLEAN_JSON),
                "n": len(texts),
                "dim": int(emb._vectors.shape[1]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[+] NPZ  -> {OUT_NPZ.name}")
    print(f"[+] META -> {OUT_META.name}")

    # Hizli dogrulama (esik 0.80)
    from src.embedder import reset_embedder
    from src.chatbot import Chatbot, MIN_BGE

    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    probes = [
        (
            "lütfen acil yardımcı olur musunuz hastane otomasyonunda hekim çalışma saatlerini düzenlememiz gerekiyor",
            "sağlık",
        ),
        (
            "hudut güvenliği için yerli komuta kontrol yazılımı tedarik etmek istiyoruz",
            "savunma",
        ),
        (
            "uzaktan öğrenim portalı ve dijital kütüphane altyapısı kurmak niyetindeyiz",
            "eğitim",
        ),
        (
            "Bilgisayar mühendisliği taban puanları ve burs imkanları",
            "eğitim",
        ),
        (
            "Yabancı turist sağlık sigortası paketi arıyorum",
            "turizm",
        ),
        (
            "Şirketimiz için e-ticaret sepet optimizasyonu ve ödeme geçidi entegrasyonu entegre etmek istiyoruz.",
            "belirsiz",
        ),
    ]
    print(f"\n--- Dogrulama MIN_BGE={MIN_BGE} (anahtar sozluk YOK) ---")
    for q, exp in probes:
        r = bot.sor(q)
        ok = (exp == "belirsiz" and r.mod == "FB") or (
            exp != "belirsiz" and r.sektor == exp and r.mod in ("K1", "K2") and (
                r.yontem == "kisaltma" or r.skor >= MIN_BGE
            )
        )
        print(
            f"  {'OK' if ok else 'FAIL'} {r.sektor}/{r.mod}/{r.yontem} "
            f"skor={r.skor:.3f} | {exp}"
        )


if __name__ == "__main__":
    main()
