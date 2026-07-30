"""
BGE Eşik Kalibrasyon Scripti
Başarısız senaryoların gerçek BGE skorlarını rapor eder.
MIN_BGE için optimal eşik önerir.
"""
import sys, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, ChatbotResponse

# 36 orijinal senaryo (sadece 4 sektör)
SENARYOLAR = [
    ("A1", "Saglik sektorunde faaliyet gosteriyoruz.", "saglik", "K2"),
    ("A2", "Sagligimiz icin bir sistem ariyoruz.", "belirsiz", "FB"),
    ("A3", "Saglikla ilgili bir yazilim istiyoruz.", "belirsiz", "FB"),
    ("A4", "Hastaneler icin randevu sistemi ariyoruz.", "saglik", "K2"),
    ("A5", "Klinigimiz icin hasta takip yazilimi lazim.", "saglik", "K2"),
    ("A6", "Hekim takvimi ve muayene kaydi tutacak bir sistem istiyoruz.", "saglik", "K2"),
    ("A7", "Poliklinigimiz icin tele-tip altyapisi ariyoruz.", "saglik", "K2"),
    ("A8", "Saglik sektorunde otomasyon projeleri gelistiriyoruz.", "saglik", "K2"),
    ("B1", "Turizm sektorundeyiz.", "turizm", "K2"),
    ("B2", "Turizmle ugrasan bir firmayiz.", "turizm", "K2"),
    ("B3", "Otelimiz icin rezervasyon sistemi ariyoruz.", "turizm", "K2"),
    ("B4", "Tatil koyu icin online rezervasyon altyapisi istiyoruz.", "turizm", "K2"),
    ("B5", "Seyahat acentesi olarak check-in cozumu ariyoruz.", "turizm", "K2"),
    ("B6", "Otel yonetim yazilimi teklifi almak istiyoruz.", "turizm", "K2"),
    ("C1", "Savunma sanayiindeyiz, yerli yazilim ariyoruz.", "savunma", "K2"),
    ("C2", "Askeri tesislerimiz icin komuta kontrol sistemi lazim.", "savunma", "K2"),
    ("C3", "Radar verilerini analiz eden bir yazilim istiyoruz.", "savunma", "K2"),
    ("C4", "NATO standartlarinda guvenli mesajlasma ariyoruz.", "savunma", "K2"),
    ("C5", "Savunma sektorunde hizmet veren bir firmayiz.", "savunma", "K2"),
    ("D1", "Egitim sektorundeyiz.", "egitim", "K2"),
    ("D2", "Uzaktan egitim platformu ariyoruz.", "egitim", "K2"),
    ("D3", "Okulumuz icin kayit sistemi lazim.", "egitim", "K2"),
    ("D4", "Okullarimzdaki ogrencileri takip edecek bir sistem ariyoruz.", "egitim", "K2"),
    ("D5", "LMS kurulumu icin teklif almak istiyoruz.", "egitim", "K2"),
    ("D6", "Universite ogrenci bilgi sistemini yenilemek istiyoruz.", "egitim", "K2"),
    ("E1", "Saglikli bir is ortakligi kurmak istiyoruz.", "belirsiz", "FB"),
    ("E2", "Turistik bir bolgede ofisimiz var ama yazilim hizmeti ariyoruz.", "belirsiz", "FB"),
    ("E3", "Egitimli personel ariyoruz, ise alim konusunda yardimci olur musunuz?", "belirsiz", "FB"),
    ("E4", "Savunma mekanizmalari guclu bir yazilim mimarisi tasarlamaliyiz.", "belirsiz", "FB"),
    ("F1", "Fiyat teklifi almak istiyorum.", "belirsiz", "FB"),
    ("F2", "Yazilim hizmetleriniz hakkinda bilgi alabilir miyim?", "belirsiz", "FB"),
    ("F3", "Demo sunum talep ediyorum.", "belirsiz", "FB"),
    ("G1", "Klinik zincirimizin operasyonel verimliligi icin hekim takvimi, hasta muayene kayitlari ve laboratuvar sonuc entegrasyonlarini kapsayan bir saglik bilisimi cozumu ariyoruz.", "saglik", "K2"),
    ("G2", "Yeni acilacak tatil koyumuz icin online rezervasyon altyapisi, misafir check-in surecleri ve oda durum kartlarini yonetecegimiz bir otel yazilimi teklifi almak istiyoruz.", "turizm", "K2"),
    ("G3", "Milli Savunma Bakanligi standartlarina uygun, siber saldirilara dayanikli ve tamamen kapali aglarda calisabilen bir askeri mesajlasma sunucusu tedarik etmeyi amaclamaktayiz.", "savunma", "K2"),
    ("G4", "Kamu kurumlarina egitim ve danismanlik hizmeti sunan bir sirketiz. Personellerimizin online sertifika sureclerini yonetecegimiz bir LMS platformu kurmak istiyoruz.", "egitim", "K2"),
]

def normalize_sektor(s):
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return s.lower().translate(tr_map)

def run():
    bot = Chatbot()
    emb = bot._get_embedder()

    print("=" * 100)
    print("BGE ESIK KALIBRASYON RAPORU — 36 Senaryo")
    print("=" * 100)

    basarisizlar = []
    basarililar = []
    tum_sonuclar = []

    for cid, girdi, bkl_sektor, bkl_mod in SENARYOLAR:
        yanit = bot.sor(girdi)
        tahmin_norm = normalize_sektor(yanit.sektor)
        beklenen_norm = normalize_sektor(bkl_sektor)
        mod_ok = (yanit.mod == bkl_mod) or (bkl_mod == "K2" and yanit.mod in ("K2","HAFIZA"))
        sektor_ok = (tahmin_norm == beklenen_norm)
        durum = sektor_ok and mod_ok

        # aciklamadan top K2 skorunu cikart
        k2_skor = 0.0
        acik = yanit.aciklama or ""
        m = re.search(r"K2=([\d.]+)", acik)
        if m:
            k2_skor = float(m.group(1))
        elif yanit.skor > 0:
            k2_skor = yanit.skor

        sonuc = {
            "id": cid,
            "girdi": girdi,
            "bkl_sektor": bkl_sektor,
            "bkl_mod": bkl_mod,
            "alinan_sektor": yanit.sektor,
            "alinan_mod": yanit.mod,
            "yontem": yanit.yontem,
            "skor": yanit.skor,
            "k2_skor": k2_skor,
            "durum": durum,
            "aciklama": acik[:80],
        }
        tum_sonuclar.append(sonuc)
        if durum:
            basarililar.append(sonuc)
        else:
            basarisizlar.append(sonuc)

    # Basarisizlari goster
    print(f"\nBASARISIZ SENARYOLAR ({len(basarisizlar)} adet) — gercek skorlar:")
    print(f"{'ID':<5} {'Beklenen':<18} {'Alinan':<18} {'Yontem':<10} {'Skor':<8} {'K2_Skor':<10} {'Girdi'}")
    print("-" * 100)
    k2_skorlar_basarisiz = []
    for s in basarisizlar:
        girdi_k = s['girdi'][:45].encode("ascii","replace").decode()
        bkl = f"{s['bkl_mod']}/{s['bkl_sektor']}"
        aln = f"{s['alinan_mod']}/{s['alinan_sektor']}".encode("ascii","replace").decode()
        print(f"[{s['id']:<3}] {bkl:<18} {aln:<18} {s['yontem']:<10} {s['skor']:<8.3f} {s['k2_skor']:<10.3f} {girdi_k}")
        if s['bkl_mod'] == "K2":  # Beklenen K2 ama FB aldiysa
            k2_skorlar_basarisiz.append((s['id'], s['k2_skor'], s['girdi'][:40]))

    # Esik analizi
    print(f"\n{'='*100}")
    print("ESIK ANALIZI — Hangi MIN_BGE degerinde kac senaryo kazanir/kaybeder?")
    print(f"{'MIN_BGE':<10} {'Basarili':<10} {'Basarisiz':<12} {'K2%':<8} {'Kazanilan FB Tuzaklar hala korunuyor mu?'}")
    print("-" * 100)

    fb_tuzak_ids = {"E1","E2","E3","E4","F1","F2","F3"}  # bunlar MUTLAKA FB olmali

    for esik in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.78, 0.80, 0.82, 0.83, 0.84, 0.85]:
        basarili_sayisi = 0
        fb_tuzak_korunuyor = True
        for s in tum_sonuclar:
            bkl_mod = s['bkl_mod']
            bkl_sektor = normalize_sektor(s['bkl_sektor'])

            if s['yontem'] == 'k1-hard':
                # K1 hard-match esige bagli degil, her zaman calisir
                alinan = normalize_sektor(s['alinan_sektor'])
                mod_ok = (s['alinan_mod'] in ("K2","HAFIZA")) if bkl_mod=="K2" else s['alinan_mod']=="FB"
                sektor_ok = (alinan == bkl_sektor)
                basarili = sektor_ok and mod_ok
            elif bkl_mod == "FB":
                # FB beklenen: esik dusunce yanlis atasabilir, kontrol et
                # Basit yaklasim: skor < esik ise FB kalir = DOGRU
                basarili = s['skor'] < esik
                if s['id'] in fb_tuzak_ids and not basarili:
                    fb_tuzak_korunuyor = False
            else:
                # K2 beklenen: skor >= esik olursa basarili
                basarili = (s['skor'] >= esik) or (s['yontem'] == 'k1-hard' and normalize_sektor(s['alinan_sektor']) == bkl_sektor)

            if basarili:
                basarili_sayisi += 1

        tuzak_str = "EVET" if fb_tuzak_korunuyor else "HAYIR - RISK!"
        print(f"{esik:<10.2f} {basarili_sayisi:<10} {36-basarili_sayisi:<12} {basarili_sayisi/36*100:<8.1f} {tuzak_str}")

    print(f"\n{'='*100}")
    print("GERCEK BGE SKORLARI (aciklamadan parse edilen, sadece basarisiz K2 beklenenler):")
    print("-" * 60)
    for cid, skor, girdi in sorted(k2_skorlar_basarisiz, key=lambda x: x[1], reverse=True):
        girdi_k = girdi.encode("ascii","replace").decode()
        print(f"  [{cid}] skor={skor:.4f} | {girdi_k}")

    print(f"\n[+] Mevcut MIN_BGE=0.85 ile sonuc: {sum(1 for s in tum_sonuclar if s['durum'])}/36")

if __name__ == "__main__":
    run()
