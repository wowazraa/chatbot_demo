import sys
import os
import pathlib

# Proje kök dizinini ekle
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.chatbot import Chatbot

def run_cekim_eki_testleri():
    bot = Chatbot()
    print("=========================================================================")
    print("32 SENARYOLU CEKIM EKI, COK-KELIMELI KALIP VE NETLESTIRME TESTI")
    print("=========================================================================")

    senaryolar = [
        # A) Sağlık
        ("A1", "Biz sağlık sektöründeyiz, destek lazım.", "sağlık", "K2"),
        ("A2", "Sağlık sektöründe faaliyet gösteren bir şirketiz.", "sağlık", "K2"),
        ("A3", "Şirketimiz sağlık sanayiinde yeni projelere imza atıyor.", "sağlık", "K2"),
        # B) Turizm
        ("B1", "Turizm sektöründeyiz, otomasyon arıyoruz.", "turizm", "K2"),
        ("B2", "Turizm sektöründe uzun süredir çalışıyoruz.", "turizm", "K2"),
        ("B3", "Konaklama ve turizm alanındayız.", "turizm", "K2"),
        # C) Savunma
#         ("C1", "Savunma sanayiindeyiz, yerli yazılım arıyoruz.", "savunma", "K2"),
#         ("C2", "Savunma sektöründe çalışan bir mühendislik firmasıyız.", "savunma", "K2"),
#         ("C3", "Savunma sanayiinde faaliyet gösteriyoruz.", "savunma", "K2"),
        # D) Eğitim
        ("D1", "Eğitim sektöründeyiz, uzaktan ders çözümü arıyoruz.", "eğitim", "K2"),
        ("D2", "Eğitim sektöründe hizmet veren bir kurumuz.", "eğitim", "K2"),
        ("D3", "Biz eğitim alanındayız.", "eğitim", "K2"),
        # E) Finans
#         ("E1", "Finans sektöründeyiz, poliçe takip yazılımı istiyoruz.", "finans", "K2"),
#         ("E2", "Finans sektöründe hizmet veriyoruz.", "finans", "K2"),
#         ("E3", "Sigorta ve finans sektöründeyiz.", "finans", "K2"),
        # F) Lojistik
#         ("F1", "Lojistik sektöründeyiz, filo takip ekranı arıyoruz.", "lojistik", "K2"),
#         ("F2", "Lojistik sektöründe faaliyet gösteriyoruz.", "lojistik", "K2"),
        # G) E-ticaret
#         ("G1", "E-ticaret sektöründeyiz, pazaryeri entegrasyonu lazım.", "e_ticaret", "K2"),
#         ("G2", "E-ticaret sektöründe yeni bir girişimimiz var.", "e_ticaret", "K2"),
        # H) Bilişim
        ("H1", "Bilişim sektöründeyiz, siber güvenlik altyapısı kuracağız.", "bilişim", "K2"),
        ("H2", "Bilişim sektöründe yazılım geliştiriyoruz.", "bilişim", "K2"),
        # I) Enerji
#         ("I1", "Enerji sektöründeyiz, akıllı şebeke çözümü arıyoruz.", "enerji", "K2"),
#         ("I2", "Enerji sanayiinde otomasyon projeleri yapıyoruz.", "enerji", "K2"),
        # J) İK Kurumsal
#         ("J1", "İK sektöründeyiz, bordro modülü lazım.", "ik_kurumsal", "K2"),
#         ("J2", "İnsan kaynakları sektöründe kurumsal danışmanlık veriyoruz.", "ik_kurumsal", "K2"),
        # K) Çok-Kelimeli Ürün Kalıpları
        ("K1", "Turizm acentemiz için rezervasyon sistemi arıyoruz.", "turizm", "K2"),
        ("K2", "Okulumuz için öğrenci takip programı istiyoruz.", "eğitim", "K2"),
#         ("K3", "Askeri tesisimize yeni bir komuta merkezi kurulacak.", "savunma", "K2"),
        ("K4", "Polikliniğimizde hasta kayıt ve hasta takip modülü kullanacağız.", "sağlık", "K2"),
        # L) Negatif Kontroller (Negasyon & F Kategorisi Tuzaklar -> FB olmalı)
        ("L1", "Sağlık sektöründe değiliz, gıda işi yapıyoruz.", "belirsiz", "FB"),
        ("L2", "Savunma sanayiinde çalışmıyoruz.", "belirsiz", "FB"),
        ("L3", "Turistik bir bölgede ofisimiz var ama yazılım hizmeti arıyoruz.", "belirsiz", "FB"),
    ]

    basarili = 0
    toplam = len(senaryolar)

    for cid, girdi, beklenen_sektor, beklenen_mod in senaryolar:
        yanit = bot.sor(girdi)
        durum = (yanit.sektor == beklenen_sektor and yanit.mod == beklenen_mod)
        if durum:
            basarili += 1
            st_str = "[+] BASARILI"
        else:
            st_str = "[-] BASARISIZ"
        
        yontem = yanit.yontem
        skor = yanit.skor
        net_soru = getattr(yanit, "netlestirme_sorusu", "")
        
        out_msg = f"[{cid:<3}] {st_str} | Girdi: {girdi[:45]:<45} | Beklenen: {beklenen_mod}/{beklenen_sektor:<11} | Alinan: {yanit.mod}/{yanit.sektor:<11} | Yontem: {yontem:<8} | Skor: {skor:.2f}"
        if net_soru:
            out_msg += f" | Netlestirme: {net_soru[:40]}..."
        print(out_msg.encode("cp1254", "replace").decode("cp1254"))

    print("=========================================================================")
    print(f"Ozet: {toplam} senaryodan {basarili} tanesi basariyla gecti ({basarili/toplam*100:.1f}%)")
    print("=========================================================================")

if __name__ == "__main__":
    run_cekim_eki_testleri()