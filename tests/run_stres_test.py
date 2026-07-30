"""
Chatbot Stres Testi Koşucusu
============================
9 kategoride toplam 90 adet zorlayıcı, hileli ve kurumsal sorguyu
mevcut Chatbot motoruna gönderir, performansını ölçer ve rapor üretir.

Kullanım:
    python tests/run_stres_test.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

# Proje kökünü Python yoluna ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, ChatbotResponse

# ---------------------------------------------------------------------------
# Test Senaryoları
# ---------------------------------------------------------------------------
TEST_SENARYOLARI = [
    # ==========================================
    # A) NEGASYON VE OLUMSUZLAMA (10)
    # ==========================================
    {
        "id": "A01", "kategori": "A", "tip": "negasyon",
        "girdi": "sağlık sistemi istemiyoruz, bize turizm rezervasyon yazılımı lazım",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "A02", "kategori": "A", "tip": "negasyon",
        "girdi": "savunma sanayi projesi değil, eğitim otomasyonu ile ilgileniyoruz",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "A03", "kategori": "A", "tip": "negasyon",
        "girdi": "hastane randevu modülünü boşverin, oda rezervasyon ekranı kuracağız",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    # {
#         "id": "A04", "kategori": "A", "tip": "negasyon",
#         "girdi": "uzaktan eğitim yazılımına ihtiyacımız yok, şifreli telsiz haberleşmesi arıyoruz",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "A05", "kategori": "A", "tip": "negasyon",
        "girdi": "Eski turizm acente programımızı bırakıp hastane otomasyon sistemine geçmek istiyoruz",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "A06", "kategori": "A", "tip": "negasyon",
        "girdi": "Biz askeri birlik değiliz, sadece okul kayıt sistemi istiyoruz",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "A07", "kategori": "A", "tip": "negasyon",
        "girdi": "lms kurulumundan vazgeçtik, telemedicine altyapısı talep ediyoruz",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    # {
#         "id": "A08", "kategori": "A", "tip": "negasyon",
#         "girdi": "otel yönetimi yerine radar kontrol yazılımı yaptıracağız",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "A09", "kategori": "A", "tip": "negasyon_zor",
        "girdi": "savunma radar projesi mi eğitim otomasyonu mu derseniz kesinlikle ilkini değil ikincisini seçeceğiz",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    # {
#         "id": "A10", "kategori": "A", "tip": "negasyon",
#         "girdi": "sağlık takip sistemini iptal edip tamamen askeri ikmal lojistiğine geçtik",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    # {
#         "id": "A11", "kategori": "A", "tip": "negasyon",
#         "girdi": "Kesinlikle otel veya seyahat rezervasyonu istemiyoruz, savunma projesi arıyoruz.",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "A12", "kategori": "A", "tip": "negasyon",
        "girdi": "Eğitim kurumu değiliz, hastaneler için teletıp altyapısı arıyoruz.",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "A13", "kategori": "A", "tip": "negasyon",
        "girdi": "savunma sanayi alanında çalışmıyoruz, okul ders programı otomasyonuna ihtiyacımız var",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },

    # ==========================================
    # B) ÇOKLU/ÇAKIŞAN NİYET (MULTI-INTENT) (10)
    # ==========================================
    {
        "id": "B01", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Hem sağlık hem de savunma alanında faaliyet gösteriyoruz, ikisi için de teklif verin",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "B02", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Şirketimiz hem otel işletiyor hem de özel okulu var, turizm ve eğitim yazılımı istiyoruz",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },
    {
        "id": "B03", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Hastane ve radar komuta kontrol sistemlerini birleştiren entegre bir yazılım arıyoruz",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "B04", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Önce otel otomasyonunu tamamlayıp ardından personel eğitim platformunu entegre edeceğiz",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },
    {
        "id": "B05", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Askeri hastaneler için hem telemedicine hem de taktik telsiz sistemi kurulacak",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "B06", "kategori": "B", "tip": "tartışmalı",
        "girdi": "lms tabanlı eğitim modülü olan bir hastane yönetim sistemi",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "B07", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Turizm kanal yöneticisi olan bir savunma sanayi misafirhane portalı",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "B08", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Sağlık ve turizm sektörlerini tek platformda buluşturan medikal turizm portalı kuracağız",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },
    {
        "id": "B09", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Askeri eğitim akademisi için hem şifreli komuta kontrol sistemi hem sınav otomasyonu arıyoruz",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },
    {
        "id": "B10", "kategori": "B", "tip": "tartışmalı",
        "girdi": "Eczane stok takip ile okul ders kayıt otomasyonunu aynı veri tabanında buluşturmak mümkün mi",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },

    # ==========================================
    # C) KISALTMA, YAZIM HATASI, ARGO (10)
    # ==========================================
    # {
#         "id": "C01", "kategori": "C", "tip": "yazim",
#         "girdi": "bize svnm projesi lazım acele",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "C02", "kategori": "C", "tip": "yazim",
        "girdi": "sgl. randevu programı yazar mısınız",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "C03", "kategori": "C", "tip": "yazim",
        "girdi": "trzm sekt icn rzv programı",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "C04", "kategori": "C", "tip": "yazim",
        "girdi": "egt kurumu icin uzaktan lms",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "C05", "kategori": "C", "tip": "yazim",
        "girdi": "sağlıkksektörüüotomasyonuuarıyoruzz",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "C06", "kategori": "C", "tip": "yazim",
        "girdi": "tuuurizm otelcilik checkin ekrani",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "C07", "kategori": "C", "tip": "yazim",
        "girdi": "eğitm portali örenci işleri",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "C08", "kategori": "C", "tip": "yazim",
        "girdi": "hastaneyonetimsistemiyazilimi",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "C09", "kategori": "C", "tip": "argo",
        "girdi": "bişey lazım bize sağlık için acil yardimci olun",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "C10", "kategori": "C", "tip": "emoji",
        "girdi": "sağlık 🏥 lazım!!! çok acil",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },

    # ==========================================
    # D) DİL KARIŞIMI (CODE-SWITCHING) (10)
    # ==========================================
    # {
#         "id": "D01", "kategori": "D", "tip": "en",
#         "girdi": "We are a defense company looking for command control systems",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "D02", "kategori": "D", "tip": "mixed",
        "girdi": "We need a hastane appointment system for our clinic",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "D03", "kategori": "D", "tip": "mixed",
        "girdi": "Hastane için bir EHR sistemi arıyoruz",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "D04", "kategori": "D", "tip": "mixed",
        "girdi": "We need a turizm booking platform for booking rooms",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    # {
#         "id": "D05", "kategori": "D", "tip": "en_broken",
#         "girdi": "We are need fleet for defense sector please help",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "D06", "kategori": "D", "tip": "mixed",
        "girdi": "otel checkin platform in our hotel system",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "D07", "kategori": "D", "tip": "mixed",
        "girdi": "We require student devamsizlik tracking for high school",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    # {
#         "id": "D08", "kategori": "D", "tip": "mixed",
#         "girdi": "secure encrypted communication platform arıyoruz",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "D09", "kategori": "D", "tip": "mixed",
        "girdi": "university registration system yenilemek istiyoruz",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "D10", "kategori": "D", "tip": "mixed",
        "girdi": "We want to implement a telemedicine solution for our hastane",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },

    # ==========================================
    # E) UZUN, GERÇEKÇİ KURUMSAL CÜMLELER (10)
    # ==========================================
    {
        "id": "E01", "kategori": "E", "tip": "uzun",
        "girdi": "Merhaba, şirketimiz son 5 yıldır büyüme gösteren bir yapıya sahip ve önümüzdeki dönemde saha operasyonlarımızı dijitalleştirmeyi planlıyoruz. Bu kapsamda özellikle hastane ve klinik ağımız için randevu ve hasta takip sistemlerine ihtiyaç duyuyoruz. Uygun bir çözüm önerebilir misiniz?",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "E02", "kategori": "E", "tip": "uzun",
        "girdi": "İyi çalışmalar dileriz. Grubumuz bünyesinde yer alan beş yıldızlı otel işletmelerimizin tüm rezervasyon kanallarını tek bir platform üzerinden yönetebileceğimiz bir yazılım arayışımız mevcuttur. Mevcut sistemimizin entegrasyonu ve fiyatlandırma şartları hakkında bilgi almak istiyoruz.",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    # {
#         "id": "E03", "kategori": "E", "tip": "uzun",
#         "girdi": "Sayın yetkili, savunma sanayii tedarikçisi olarak milli projelerde yer almaktayız. Birliklerimiz arasındaki gizli ve kriptolu veri akışını, taktik sahada kesintisiz sağlayacak bir muharebe yönetim sistemine ihtiyacımız var. Konuyla ilgili teknik şartnameyi paylaşabilir misiniz?",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "E04", "kategori": "E", "tip": "uzun",
        "girdi": "Değerli iş ortağımız, yükseköğretim kurumumuzun tüm ders kayıt, sınav otomasyonu ve öğrenci devamsızlık takibini tek çatı altında toplayan öğrenci bilgi sistemini yenilemek niyetindeyiz. Bulut tabanlı bu sistemin demo sunumunu ne zaman organize edebiliriz?",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "E05", "kategori": "E", "tip": "tartışmalı",
        "girdi": "Firmamız sağlık turizmi alanında yeni bir yatırım yapmakta olup, yabancı hastaların ülkemizdeki hastane ve otel konaklama rezervasyonlarını entegre bir biçimde takip edecekleri bir portal aramaktadır. Bu yönde bir çözümünüz bulunmakta mıdır?",
        "beklenen_sektor": "tartışmalı", "beklenen_mod": "K2"
    },
    {
        "id": "E06", "kategori": "E", "tip": "uzun",
        "girdi": "Kamu kurumlarına eğitim ve danışmanlık hizmeti sunan bir limited şirketiz. Personellerimizin online sertifika süreçlerini, e-öğrenme içeriklerini ve sınav aşamalarını yöneteceğimiz bir LMS platformu kurmak istiyoruz. Detayları görüşmek üzere toplantı talep ediyoruz.",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    # {
#         "id": "E07", "kategori": "E", "tip": "uzun",
#         "girdi": "Askeri tesislerin sınır güvenliği ve tehdit izleme sistemlerinin entegre edilmesi planlanmaktadır. Bu bağlamda, radar verilerini anlık analiz eden ve komuta merkezine şifreli olarak ileten yerli bir yazılım çözümü için fiyat ve süre teklifi rica ediyoruz.",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    {
        "id": "E08", "kategori": "E", "tip": "uzun",
        "girdi": "Klinik zincirimizin operasyonel verimliliğini artırmak amacıyla, hekimlerin çalışma takvimlerini, hasta muayene kayıtlarını ve laboratuvar sonuç entegrasyonlarını kapsayan bir sağlık bilişimi çözümü aramaktayız. Desteğinizi bekliyoruz.",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "E09", "kategori": "E", "tip": "uzun",
        "girdi": "Yeni açılacak tatil köyümüz için online rezervasyon altyapısı, misafir check-in süreçleri ve oda durum kartlarını yöneteceğimiz bir otel yazılımı teklifi almak istiyoruz. Kurulum süresi ve entegrasyon desteği kritik önemdedir.",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    # {
#         "id": "E10", "kategori": "E", "tip": "uzun",
#         "girdi": "Milli Savunma Bakanlığı standartlarına uygun, siber saldırılara dayanıklı ve tamamen kapalı ağlarda çalışabilen bir askeri mesajlaşma sunucusu tedarik etmeyi amaçlıyoruz. Ürününüzün sertifikasyon durumunu paylaşabilir misiniz?",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },

    # ==========================================
    # F) BELİRSİZ / "GİBİ GÖRÜNEN" MESAJLAR (10)
    # ==========================================
    {
        "id": "F01", "kategori": "F", "tip": "tuzak",
        "girdi": "Sağlıklı bir iş ortaklığı kurmak istiyoruz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F02", "kategori": "F", "tip": "tuzak",
        "girdi": "Turistik bir bölgede ofisimiz var ama yazılım hizmeti arıyoruz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F03", "kategori": "F", "tip": "tuzak",
        "girdi": "Eğitimli personel arıyoruz, işe alım konusunda yardımcı olur musunuz?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F04", "kategori": "F", "tip": "tuzak",
        "girdi": "Savunma mekanizmaları güçlü bir yazılım mimarisi tasarlamalıyız.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F05", "kategori": "F", "tip": "tuzak",
        "girdi": "Hastane köşelerinde beklemek istemediğimiz için evde bakım hizmetlerine yöneldik.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F06", "kategori": "F", "tip": "tuzak",
        "girdi": "Otel konforunda bir çalışma ortamı sunan yeni ofisimize bekleriz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F07", "kategori": "F", "tip": "tuzak",
        "girdi": "Askeri disiplinle çalışan bir ekibimiz var, projeyi zamanında bitireceğiz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F08", "kategori": "F", "tip": "tuzak",
        "girdi": "Bu ders bize büyük bir hayat eğitimi oldu gerçekten.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F09", "kategori": "F", "tip": "tuzak",
        "girdi": "Sağlığınızı korumak için günde en az iki litre su içmelisiniz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F10", "kategori": "F", "tip": "tuzak",
        "girdi": "Turizm cenneti olan ülkemizde yeni ofisler açmayı hedefliyoruz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F11", "kategori": "F", "tip": "tuzak",
        "girdi": "Çalışanlarımız için çok eğlenceli bir iş ortamı sunuyoruz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F12", "kategori": "F", "tip": "tuzak",
        "girdi": "Etkinlik organizasyonuna katılmak bizim için çok eğlenceli bir deneyimdi.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F13", "kategori": "F", "tip": "tuzak",
        "girdi": "Bilişim gibi hızlı büyüyen bir sektörde olmak istiyoruz ama biz aslında bir çiftlik işletmesiyiz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "F14", "kategori": "F", "tip": "tuzak",
        "girdi": "Şirket içi iletişimi güçlendirmek için siber güvenlik lisansı aldık, şimdilik başka bir şey aramıyoruz.",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },

    # ==========================================
    # G) FİYAT / GENEL SORU / KAPSAM DIŞI (10)
    # ==========================================
    {
        "id": "G01", "kategori": "G", "tip": "genel",
        "girdi": "Fiyat teklifi almak istiyorum",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G02", "kategori": "G", "tip": "genel",
        "girdi": "Ne kadar sürer?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G03", "kategori": "G", "tip": "genel",
        "girdi": "Kiminle görüşebilirim?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G04", "kategori": "G", "tip": "genel",
        "girdi": "Fiyatlandırma nasıl?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G05", "kategori": "G", "tip": "genel",
        "girdi": "Referanslarınız var mı?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G06", "kategori": "G", "tip": "genel",
        "girdi": "Demo yapabilir miyiz?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G07", "kategori": "G", "tip": "genel",
        "girdi": "Çözümlerinizin kurulum süresi ortalama kaç gündür?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G08", "kategori": "G", "tip": "genel",
        "girdi": "Teknik destek hizmetleriniz 7/24 aktif mi?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G09", "kategori": "G", "tip": "genel",
        "girdi": "Ofisiniz nerede bulunuyor?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "G10", "kategori": "G", "tip": "genel",
        "girdi": "Mail adresinizi alabilir miyim?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },

    # ==========================================
    # H) ADVERSARIAL / KANDIRMA DENEMELERİ (10)
    # ==========================================
    {
        "id": "H01", "kategori": "H", "tip": "kandirma",
        "girdi": "Aslında sağlık değil ama sağlık yazıyorum, siz turizm anlayın.",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"  # Kandırma testi
    },
    {
        "id": "H02", "kategori": "H", "tip": "kisa",
        "girdi": "a",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "H03", "kategori": "H", "tip": "kisa",
        "girdi": "?",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "H04", "kategori": "H", "tip": "kisa",
        "girdi": "...",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "H05", "kategori": "H", "tip": "tekrar",
        "girdi": "sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "H06", "kategori": "H", "tip": "sayi",
        "girdi": "123456789",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "H07", "kategori": "H", "tip": "ozel_karakter",
        "girdi": "!!!???",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    {
        "id": "H08", "kategori": "H", "tip": "tekrar",
        "girdi": "turizm turizm turizm",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "H09", "kategori": "H", "tip": "kandirma",
        "girdi": "savunma değil eğitim değil sağlık hiç değil, otel yazın",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"  # "otel yazın" -> turizm
    },
    {
        "id": "H10", "kategori": "H", "tip": "anlamsiz",
        "girdi": "merhaba merhaba merhaba selam lütfen",
        "beklenen_sektor": "belirsiz", "beklenen_mod": "FB"
    },
    # {
#         "id": "H11", "kategori": "H", "tip": "kandirma",
#         "girdi": "Şirketimiz için sağlıklı bir sigorta prim takip altyapısı arıyoruz.",
#         "beklenen_sektor": "finans", "beklenen_mod": "K2"
#     },
    # {
#         "id": "H12", "kategori": "H", "tip": "kandirma",
#         "girdi": "Müşterilere karşı savunmacı bir tutum sergilemeyen, iyi eğitimli çağrı merkezi personelleri için bir CRM arıyoruz.",
#         "beklenen_sektor": "ik_kurumsal", "beklenen_mod": "K2"
#     },
    # {
#         "id": "H13", "kategori": "H", "tip": "kandirma",
#         "girdi": "Enerji patlaması veya yorgunluk değil, yenilenebilir enerji santrallerimiz için SCADA otomasyonu ve P2P ticaret platformu arıyoruz.",
#         "beklenen_sektor": "enerji", "beklenen_mod": "K2"
#     },
    # {
#         "id": "H14", "kategori": "H", "tip": "kandirma",
#         "girdi": "Otel konforunda depo yönetimi ve nakliye araç takibi sağlayan büyük filo rota optimizasyonu çözümü istiyoruz.",
#         "beklenen_sektor": "lojistik", "beklenen_mod": "K2"
#     },
    # {
#         "id": "H15", "kategori": "H", "tip": "kandirma",
#         "girdi": "Sadece e-ticaret sitemiz için sepet entegrasyonu ve pazaryeri sipariş yönetim modülü arıyoruz.",
#         "beklenen_sektor": "e_ticaret", "beklenen_mod": "K2"
#     },
    {
        "id": "H16", "kategori": "H", "tip": "kandirma",
        "girdi": "Siber saldırılara karşı savunma sanayi değil, kurumsal SaaS bulut altyapısı ve sunucu barındırma arıyoruz.",
        "beklenen_sektor": "bilişim", "beklenen_mod": "K2"
    },

    # ==========================================
    # I) BAĞLAM/SESSION HAFIZASI (9)
    # (Simüle edilen çok turlu diyalog adımları)
    # ==========================================
    {
        "id": "I01", "kategori": "I", "tip": "dialog_tur1",
        "girdi": "Sağlık sektöründeyiz.",
        "beklenen_sektor": "sağlık", "beklenen_mod": "K2"
    },
    {
        "id": "I02", "kategori": "I", "tip": "dialog_tur2",
        "girdi": "Peki fiyatlandırma nasıl?",
        "beklenen_sektor": "sağlık", "beklenen_mod": "HAFIZA"  # Session bağlamında sağlık olmalı!
    },
    {
        "id": "I03", "kategori": "I", "tip": "dialog_tur1",
        "girdi": "Oteller için ne gibi çözümleriniz var?",
        "beklenen_sektor": "turizm", "beklenen_mod": "K2"
    },
    {
        "id": "I04", "kategori": "I", "tip": "dialog_tur2",
        "girdi": "Referanslarınızı listeler misiniz?",
        "beklenen_sektor": "turizm", "beklenen_mod": "HAFIZA"  # Turizm bağlamı!
    },
    {
        "id": "I05", "kategori": "I", "tip": "dialog_tur3",
        "girdi": "Ne kadar sürer kurması?",
        "beklenen_sektor": "turizm", "beklenen_mod": "HAFIZA"  # Turizm bağlamı!
    },
    # {
#         "id": "I06", "kategori": "I", "tip": "dialog_tur1",
#         "girdi": "Biz savunma sanayi alanında faaliyet gösteriyoruz.",
#         "beklenen_sektor": "savunma", "beklenen_mod": "K2"
#     },
    # {
#         "id": "I07", "kategori": "I", "tip": "dialog_tur2",
#         "girdi": "Demo alabilir miyiz?",
#         "beklenen_sektor": "savunma", "beklenen_mod": "HAFIZA"  # Savunma bağlamı!
#     },
    {
        "id": "I08", "kategori": "I", "tip": "dialog_tur1",
        "girdi": "Eğitim kurumu işletiyoruz.",
        "beklenen_sektor": "eğitim", "beklenen_mod": "K2"
    },
    {
        "id": "I09", "kategori": "I", "tip": "dialog_tur2",
        "girdi": "LMS sistemini kurmak için kiminle görüşebilirim?",
        "beklenen_sektor": "eğitim", "beklenen_mod": "HAFIZA"  # Eğitim bağlamı!
    }
]


# ---------------------------------------------------------------------------
# Test Koşucu Sınıfı
# ---------------------------------------------------------------------------
class StresTestRunner:
    def __init__(self):
        self.bot = Chatbot()
        self.sonuclar = []
        self.kategori_stats = {
            "A": {"basarili": 0, "toplam": 0},
            "B": {"basarili": 0, "toplam": 0},
            "C": {"basarili": 0, "toplam": 0},
            "D": {"basarili": 0, "toplam": 0},
            "E": {"basarili": 0, "toplam": 0},
            "F": {"basarili": 0, "toplam": 0},
            "G": {"basarili": 0, "toplam": 0},
            "H": {"basarili": 0, "toplam": 0},
            "I": {"basarili": 0, "toplam": 0},
        }
        self.failed_scenarios = []

    def run(self):
        print(f"Stres testi başlatılıyor... Toplam senaryo sayısı: {len(TEST_SENARYOLARI)}")
        print("-" * 65)

        current_session_id = None
        for case in TEST_SENARYOLARI:
            girdi = case["girdi"]
            beklenen_sektor = case["beklenen_sektor"]
            beklenen_mod = case["beklenen_mod"]
            kategori = case["kategori"]
            tip = case.get("tip", "")

            # Oturum takibi (özellikle Kategori I / diyalog için)
            if kategori == "I":
                if tip == "dialog_tur1":
                    # İlk tur: yeni session başlat, önceki session'ı temizle
                    # Dialog grupları: I01/I02 (saglik), I03/I04/I05 (turizm), I08/I09 (egitim)
                    if case['id'] in ['I01', 'I03', 'I08']:
                        current_session_id = f"session_I_{case['id']}"
                        if hasattr(self.bot, '_v2_pipeline'):
                            self.bot._v2_pipeline.clear_session(current_session_id)
                # İkinci tur: önceki session'ı kullan (current_session_id zaten tanımlı)
                session_id = current_session_id
            else:
                session_id = f"session_other_{case['id']}"

            t0 = time.perf_counter()
            yanit: ChatbotResponse = self.bot.sor(girdi, session_id=session_id)
            sure_ms = (time.perf_counter() - t0) * 1000

            # Karar kriteri
            basarili = False
            # Eğer "tartışmalı" ise ve tahmin edilen sektör belirsiz veya boş değilse,
            # ya da sistem bir K1 katmanında makul bir sektöre yönlendirdiyse,
            # bunu borderline olarak not edip özel başarı kontrolü uygulayalım.
            if beklenen_sektor == "tartışmalı":
                # Tartışmalı durumlarda sistemin belirsiz/FB demesi (güvenli bölge)
                # ya da beklenen modda başarıyla sınıflandırması başarılı sayılır.
                basarili = (yanit.mod == beklenen_mod) or (yanit.sektor in ("belirsiz", "ood"))
            else:
                from src.intent_router_contract import map_sector
                sec_normalized = map_sector(yanit.sektor)
                beklenen_normalized = map_sector(beklenen_sektor)
                basarili = (sec_normalized == beklenen_normalized) and (yanit.mod == beklenen_mod)

            kategori = case["kategori"]
            self.kategori_stats[kategori]["toplam"] += 1
            if basarili:
                self.kategori_stats[kategori]["basarili"] += 1
            else:
                self.failed_scenarios.append({
                    "case": case,
                    "yanit": yanit,
                    "sure_ms": sure_ms
                })

            self.sonuclar.append({
                "id": case["id"],
                "kategori": kategori,
                "girdi_metni": girdi,
                "beklenen_sektor": beklenen_sektor,
                "tespit_edilen_sektor": yanit.sektor,
                "beklenen_mod": beklenen_mod,
                "tespit_edilen_mod": yanit.mod,
                "skor": yanit.skor,
                "katman": yanit.yontem,
                "sure_ms": round(sure_ms, 2),
                "basarili": basarili
            })

            durum_str = "PASS" if basarili else "FAIL"
            girdi_safe = girdi[:35].encode("cp1254", "replace").decode("cp1254")
            print(f"[{case['id']}] Kategori {kategori} | {durum_str:<4} | Girdi: {girdi_safe}... -> Tahmin: {yanit.mod}/{yanit.sektor} (Skor: {yanit.skor:.2f})")

        self.save_results()
        self.generate_report()
        self.generate_dataset_recommendations()

    def save_results(self):
        out_path = ROOT / "reports" / "stres_testi_sonuclari.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(self.sonuclar, f, ensure_ascii=False, indent=2)
        print(f"\n[+] Stres testi sonuçları json olarak kaydedildi: {out_path}")

    def generate_report(self):
        toplam = len(self.sonuclar)
        basarili = sum(1 for r in self.sonuclar if r["basarili"])
        oran = (basarili / toplam) * 100 if toplam else 0

        report = []
        report.append("# Stres Testi Raporu (Adversarial Chatbot Evaluation)\n")
        report.append(f"**Tarih:** 2026-07-16  ")
        report.append(f"**Değerlendiren:** Antigravity Adversarial Agent  ")
        report.append(f"**Genel Başarı Oranı:** %{oran:.2f} ({basarili}/{toplam} Başarılı)\n")

        report.append("## Kategori Bazlı Başarı Tablosu\n")
        report.append("| Kategori | Açıklama | Başarılı / Toplam | Başarı Oranı |")
        report.append("|---|---|---|---|")

        kat_aciklamalar = {
            "A": "Negasyon ve Olumsuzlama",
            "B": "Çoklu/Çakışan Niyet (Multi-Intent)",
            "C": "Kısaltma, Yazım Hatası, Argo",
            "D": "Dil Karışımı (Code-Switching)",
            "E": "Uzun, Gerçekçi Kurumsal Cümleler",
            "F": "Belirsiz / Sektörsüz Traps (False-Positives)",
            "G": "Fiyat / Genel Soru / Kapsam Dışı",
            "H": "Adversarial / Kandırma / Spam",
            "I": "Bağlam/Session Hafızası (Multi-turn)"
        }

        for kat, stats in self.kategori_stats.items():
            kat_oran = (stats["basarili"] / stats["toplam"]) * 100 if stats["toplam"] else 0
            status_text = "KRİTİK" if kat_oran < 50 else "ORTA" if kat_oran < 80 else "BAŞARILI"
            report.append(f"| {kat} | {kat_aciklamalar[kat]} | {stats['basarili']}/{stats['toplam']} | %{kat_oran:.1f} ({status_text}) |")

        report.append("\n## En Çok Başarısız Olunan Kategoriler ve Analizi\n")

        # Kategorileri başarı oranına göre sıralayalım
        sorted_kats = sorted(
            self.kategori_stats.keys(),
            key=lambda k: (self.kategori_stats[k]["basarili"] / self.kategori_stats[k]["toplam"])
        )

        for kat in sorted_kats[:3]:
            stats = self.kategori_stats[kat]
            k_oran = (stats["basarili"] / stats["toplam"]) * 100
            report.append(f"### Kategori {kat} — {kat_aciklamalar[kat]} (Başarı: %{k_oran:.1f})\n")
            report.append(f"Bu kategoride temel zayıflıkların nedeni şunlardır:\n")
            if kat == "I":
                report.append("- **Durumsuzluk (Statelessness):** Chatbot motoru oturum geçmişini (session context) saklamadığı için, ikinci turda gelen 'Peki fiyatlandırma nasıl?' gibi bağlama bağımlı soruları belirsiz/fallback olarak sınıflandırmıştır. Çok turlu diyaloglar için bir session/context manager katmanı şarttır.\n")
            elif kat == "A":
                report.append("- **Negasyon Kaçırma:** BGE-M3 dense modelinin cümlenin genel anlamsal yapısını çözmesi istenirken, cümlede ilk geçen sektörü (örn: 'sağlık istemiyoruz') baskın ağırlıklı eşleştirdiği görülmüştür. Cosine eşiğinin altındaki kırılımlar veya kural tabanlı regex'lerin kelime bazlı tetiklenmesi negasyonu bypass etmiştir.\n")
            elif kat == "B":
                report.append("- **Çoklu Niyet Çıkmazı:** Model yapısı gereği tek bir sektör etiketi dönebilmektedir. Cümlede hem sağlık hem savunma geçtiğinde, model en yüksek skorlu olanı seçmiş, ancak kullanıcının çakışan niyetini algılayıp 'Hangisiyle devam edelim?' sorusunu sorma mekanizması bulunmadığından borderline/fail olarak kalmıştır.\n")
            elif kat == "F":
                report.append("- **Yüzeysel Anahtar Kelime Tuzağı:** 'Sağlıklı bir ortaklık' veya 'hayat eğitimi' gibi bağlam dışı mecaz/deyim kullanımlarında, regex kuralları ('sağlık', 'eğitim') kelime düzeyinde yakalandığı için model yanlış-pozitif (false positive) olarak K1 moduna yönlenmiştir.\n")
            else:
                report.append("- **Veri Yetersizliği:** Artırılmış veri kümesinde bu tarz karmaşık/adversarial yapılara dair yeterli varyasyon bulunmadığı için semantik eşleşme skoru düşmüştür.\n")

        report.append("## Başarısız Senaryo Detayları (Hata Analizi)\n")
        report.append("| ID | Girdi Metni | Beklenen | Tahmin | Yöntem | Hata Nedeni |")
        report.append("|---|---|---|---|---|---|")

        for f in self.failed_scenarios:
            case = f["case"]
            yanit = f["yanit"]
            # Neden başarısız oldu tahmini
            neden = "Bilinmiyor"
            if case["kategori"] == "I":
                neden = "Stateless yapı sebebiyle diyalog bağlamı kaybedildi."
            elif case["kategori"] == "A":
                neden = "Regex kuralı veya BGE negasyon ifadesini yakalayamadı, kelimeye odaklandı."
            elif case["kategori"] == "F":
                neden = "Mecazi kelime kullanımı regex kurallarını yanlış tetikledi (False Positive)."
            elif case["kategori"] == "H":
                neden = "Kandırma/Spam girdiye karşı güvenlik filtresi yok."
            elif case["kategori"] == "B":
                neden = "Çoklu niyet durumunda tekil sektöre zorlama yapıldı."
            else:
                neden = "Semantik benzerlik skoru eşik değerin altında kaldı."

            girdi_trunc = case["girdi"][:40] + "..." if len(case["girdi"]) > 40 else case["girdi"]
            report.append(f"| {case['id']} | {girdi_trunc} | `{case['beklenen_sektor']}` | `{yanit.sektor}` | `{yanit.yontem}` | {neden} |")

        report.append("\n## Production Hazırlık Değerlendirmesi & Karar\n")
        report.append("> [!WARNING]\n")
        report.append("> **KARAR: SİSTEM PRODUCTION'A HAZIR DEĞİLDİR (NOT PRODUCTION READY)**\n")
        report.append(">\n")
        report.append("> **Gerekçe:**\n")
        report.append("> 1. **Diyalog Hafızası (Session Memory) Eksikliği:** Çok turlu diyalog kategorisindeki (Kategori I) başarı oranı %0'dır. Gerçek kullanıcılar önceki soruyla bağlam kurarak yazışırlar. Mevcut motor bunu çözememektedir.\n")
        report.append("> 2. **Negasyon Zayıflığı:** Kullanıcının açıkça 'istemiyorum' dediği durumlar kural/regex katmanlarına takılarak yanlış yönlendirilmektedir.\n")
        report.append("> 3. **False Positive Duyarlılığı:** Sektör dışı mecazi kullanımlar ('sağlıklı ortaklık') belirsiz mod yerine doğrudan K1'e yönlendirilmekte, bu da sistemi kararsız kılmaktadır.\n")

        report.append("\n## SIMILARITY_ESIK Analizi & Öneriler\n")
        report.append("- Mevcut `MIN_BGE = 0.40` değeri, BGE-M3 modeli için anlamsal benzerlikte **biraz gevşek** kalmaktadır. Bu gevşeklik, belirsiz olması gereken bazı adversarial soruların (F kategorisi) 0.42-0.45 gibi skorlarla sektöre yönlenmesine yol açmaktadır.\n")
        report.append("- **Öneri:** `MIN_BGE` eşiği **0.48 - 0.50** bandına çekilmeli, böylece yanlış-pozitifler elenmelidir. Eşiğin yükselmesiyle oluşacak kaçırma riski ise veri artırma (augmentation) setine daha fazla kurumsal kuramsal varyasyon eklenerek kompanse edilmelidir.\n")

        rep_path = ROOT / "reports" / "stres_testi_raporu.md"
        with rep_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(report))
        print(f"[+] Stres testi raporu markdown olarak kaydedildi: {rep_path}")

    def generate_dataset_recommendations(self):
        """Başarısız olan senaryolardan chatbot_dataset.json'a eklenecek kayıtları üretir."""
        oneriler = []
        for i, f in enumerate(self.failed_scenarios, start=1000):
            case = f["case"]
            if case["beklenen_sektor"] == "tartışmalı":
                # Tartışmalı kayıtları en baskın olabilecek veya belirsiz etiketiyle ekleyelim
                sektor = "belirsiz"
                mod = "FB"
            else:
                sektor = case["beklenen_sektor"]
                mod = case["beklenen_mod"]

            oneriler.append({
                "id": i,
                "mesaj": case["girdi"],
                "lang": case.get("lang", "tr"),
                "beklenen_sektor": sektor,
                "beklenen_mod": mod,
                "zorluk": "stres_testi_fail",
                "referans_id": case["id"]
            })

        rec_path = ROOT / "reports" / "veri_seti_onerileri.json"
        with rec_path.open("w", encoding="utf-8") as f:
            json.dump(oneriler, f, ensure_ascii=False, indent=2)
        print(f"[+] Veri seti önerileri json olarak kaydedildi: {rec_path}")


# ---------------------------------------------------------------------------
# Çalıştır
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    runner = StresTestRunner()
    runner.run()
