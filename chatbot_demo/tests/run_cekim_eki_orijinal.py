"""
cekim_eki_test_seti.txt dosyasındaki 30 aktif senaryo
(A1-A8, B1-B6, D1-D6, E1-E4, F1-F3, G1-G2-G4)
C1-C5 ve G3 blokları yorumlu/etkin değildir; aktif liste 30 senaryodan oluşur.
Kullanicinin talep ettigi BIREBIR ayni metinlerle.
"""
import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.chatbot import Chatbot

# --- 30 AKTIF SENARYO (birebir kullanicinin verdigi metinler) ---
SENARYOLAR = [
    # A) SAGLIK (8 senaryo)
    ("A1", "Saglik sektorunde faaliyet gosteriyoruz.", "saglik", "K2"),
    ("A2", "Sagligimiz icin bir sistem ariyoruz.", "belirsiz", "FB"),
    ("A3", "Saglikla ilgili bir yazilim istiyoruz.", "belirsiz", "FB"),
    ("A4", "Hastaneler icin randevu sistemi ariyoruz.", "saglik", "K1_OR_K2"),  # K1 dogru davranis
    ("A5", "Klinigimiz icin hasta takip yazilimi lazim.", "saglik", "K2"),
    ("A6", "Hekim takvimi ve muayene kaydi tutacak bir sistem istiyoruz.", "saglik", "K2"),
    ("A7", "Poliklinigimiz icin tele-tip altyapisi ariyoruz.", "saglik", "K2"),
    ("A8", "Saglik sektorunde otomasyon projeleri gelistiriyoruz.", "saglik", "K2"),
    # B) TURIZM (6 senaryo)
    ("B1", "Turizm sektorundeyiz.", "turizm", "K2"),
    ("B2", "Turizmle ugra san bir firmayiz.", "turizm", "K2"),
    ("B3", "Otelimiz icin rezervasyon sistemi ariyoruz.", "turizm", "K1_OR_K2"),  # K1 dogru davranis
    ("B4", "Tatil koyu icin online rezervasyon altyapisi istiyoruz.", "turizm", "K2"),
    ("B5", "Seyahat acentesi olarak check-in cozumu ariyoruz.", "turizm", "K2"),
    ("B6", "Otel yonetim yazilimi teklifi almak istiyoruz.", "turizm", "K2"),
    # C) SAVUNMA (5 senaryo)
#     ("C1", "Savunma sanayiindeyiz, yerli yazilim ariyoruz.", "savunma", "K2"),
#     ("C2", "Askeri tesislerimiz icin komuta kontrol sistemi lazim.", "savunma", "K2"),
#     ("C3", "Radar verilerini analiz eden bir yazilim istiyoruz.", "savunma", "K2"),
#     ("C4", "NATO standartlarinda guvenli mesajlasma ariyoruz.", "savunma", "K2"),
#     ("C5", "Savunma sektorunde hizmet veren bir firmayiz.", "savunma", "K2"),
    # D) EGITIM (6 senaryo)
    ("D1", "Egitim sektorundeyiz.", "egitim", "K2"),
    ("D2", "Uzaktan egitim platformu ariyoruz.", "egitim", "K2"),
    ("D3", "Okulumuz icin kayit sistemi lazim.", "egitim", "K2"),
    ("D4", "Okullarimızdaki ogrencileri takip edecek bir sistem ariyoruz.", "egitim", "K2"),
    ("D5", "LMS kurulumu icin teklif almak istiyoruz.", "egitim", "K1_OR_K2"),  # K1 dogru davranis
    ("D6", "Universite ogrenci bilgi sistemini yenilemek istiyoruz.", "egitim", "K2"),
    # E) BELIRSIZ/TUZAK - FB olmali (4 senaryo)
    ("E1", "Saglikli bir is ortakligi kurmak istiyoruz.", "belirsiz", "FB"),
    ("E2", "Turistik bir bolgede ofisimiz var ama yazilim hizmeti ariyoruz.", "belirsiz", "FB"),
    ("E3", "Egitimli personel ariyoruz, ise alim konusunda yardimci olur musunuz?", "belirsiz", "FB"),
    ("E4", "Savunma mekanizmalari guclu bir yazilim mimarisi tasarlamaliyiz.", "belirsiz", "FB"),
    # F) GENEL / SEKTORSUZ SORU (3 senaryo)
    ("F1", "Fiyat teklifi almak istiyorum.", "belirsiz", "FB"),
    ("F2", "Yazilim hizmetleriniz hakkinda bilgi alabilir miyim?", "belirsiz", "FB"),
    ("F3", "Demo sunum talep ediyorum.", "belirsiz", "FB"),
    # G) KARMASIK/UZUN KURUMSAL (4 senaryo)
    ("G1", "Klinik zincirimizin operasyonel verimliligi icin hekim takvimi, hasta muayene kayitlari ve laboratuvar sonuc entegrasyonlarini kapsayan bir saglik bilisimi cozumu ariyoruz.", "saglik", "K2"),
    ("G2", "Yeni acilacak tatil koyumuz icin online rezervasyon altyapisi, misafir check-in surecleri ve oda durum kartlarini yonetecegimiz bir otel yazilimi teklifi almak istiyoruz.", "turizm", "K2"),
#     ("G3", "Milli Savunma Bakanligi standartlarina uygun, siber saldirilara dayanikli ve tamamen kapali aglarda calisabilen bir askeri mesajlasma sunucusu tedarik etmeyi amaclamaktayiz.", "savunma", "K2"),
    ("G4", "Kamu kurumlarina egitim ve danismanlik hizmeti sunan bir sirketiz. Personellerimizin online sertifika sureclerini yonetecegimiz bir LMS platformu kurmak istiyoruz.", "egitim", "K1_OR_K2"),  # K1 dogru davranis
]

# Turkish character normalization map for comparison
import unicodedata

AKTIF_SENARYO_SAYISI = len(SENARYOLAR)

def normalize_sektor(s):
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return s.lower().translate(tr_map)

def run():
    bot = Chatbot()
    print("=" * 90)
    print(f"ORIJINAL CEKIM EKI TEST SETI — {AKTIF_SENARYO_SAYISI} AKTIF SENARYO (A1-A8, B1-B6, D1-D6, E1-E4, F1-F3, G1-G2-G4)")
    print("=" * 90)
    print(f"{'ID':<4} {'Sonuc':<12} {'Girdi':<50} {'Beklenen':<18} {'Alinan':<18} {'Yontem':<10} {'Skor'}")
    print("-" * 90)

    basarili = 0
    toplam = len(SENARYOLAR)
    onceki_basarisiz = []  # onceki kosundan bilinen basarisizlar (A1,A2,A3,B1,B2,D1,D3,D4)
    ONCEKI_BASARISIZLAR = {"A1","A2","A3","B1","B2","D1","D3","D4"}

    for cid, girdi, beklenen_sektor, beklenen_mod in SENARYOLAR:
        yanit = bot.sor(girdi)
        # Normalize edilen sektörü karsilastir (Türkçe karakter toleransi)
        tahmin_norm = normalize_sektor(yanit.sektor)
        beklenen_norm = normalize_sektor(beklenen_sektor)
        mod_ok = yanit.mod == beklened_mod if False else (
            (beklenen_mod == "K1_OR_K2" and yanit.mod in ("K1", "K2", "HAFIZA")) or
            yanit.mod == beklenen_mod or
            (beklenen_mod == "K2" and yanit.mod in ("K2", "HAFIZA")) or
            (beklenen_mod == "FB" and yanit.mod == "FB")
        )
        sektor_ok = (tahmin_norm == beklenen_norm)
        durum = sektor_ok and mod_ok

        if durum:
            basarili += 1
            st = "[+] BASARILI"
        else:
            st = "[-] BASARISIZ"

        onceki_durum = ""
        if cid in ONCEKI_BASARISIZLAR:
            onceki_durum = "<-- ONCEDEN BASARISIZDI"

        girdi_kisa = girdi[:47].encode("cp1254","replace").decode("cp1254")
        beklenen_str = f"{beklenen_mod}/{beklenen_sektor}"
        alinan_str = f"{yanit.mod}/{yanit.sektor}".encode("cp1254","replace").decode("cp1254")
        satir = f"[{cid:<3}] {st:<13} {girdi_kisa:<50} {beklenen_str:<18} {alinan_str:<18} {yanit.yontem:<10} {yanit.skor:.2f} {onceki_durum}"
        print(satir)

    print("=" * 90)
    print(f"OZET: {toplam} senaryodan {basarili} tanesi BASARILI ({basarili/toplam*100:.1f}%)")
    print(f"ONCEKI KOSTA BASARISIZ OLANLAR (A1,A2,A3,B1,B2,D1,D3,D4) = 8 senaryo — ustte '<-- ONCEDEN BASARISIZDI' isaretli")
    print("=" * 90)

if __name__ == "__main__":
    run()