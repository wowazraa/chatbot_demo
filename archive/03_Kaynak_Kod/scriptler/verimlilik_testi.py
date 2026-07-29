"""
Verimlilik testi (v2) — MiniLM vs BGE-M3.

Önceki test (ornek_veri.json) çok kolaydı, ikisi de %100 çıktı ve
gerçek farkı göstermedi. Bu script:
  1. Daha zor bir veri seti kullanır (zorlu_veri.json): yakın sektörler
     (sağlık/sigorta gibi), sektöre uzak/belirsiz mesajlar dahil.
  2. Bir SIMILARITY_ESIK değeri uygular — eşik altı skorlar "belirsiz"
     sayılır, bu da modelin "bilmiyorum" diyebilme başarısını da ölçer.
  3. Bellek kullanımını (psutil ile) ve gerçek çıkarım (inference)
     hızını raporlar.

Kurulum: pip install sentence-transformers psutil
Çalıştırma: python verimlilik_testi.py
"""

import json
import time
import psutil
import os
from sentence_transformers import SentenceTransformer, util

MODELLER = {
    "MiniLM (384 boyut)": "paraphrase-multilingual-MiniLM-L12-v2",
    "BGE-M3 (1024 boyut)": "BAAI/bge-m3",
}

SIMILARITY_ESIK = 0.50


def veri_yukle(path="../veri/zorlu_veri.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def bellek_mb():
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024 * 1024)


def modeli_test_et(model_adi, veri):
    print(f"\n{'=' * 70}\nModel: {model_adi}\n{'=' * 70}")

    bellek_once = bellek_mb()
    baslangic = time.time()
    model = SentenceTransformer(model_adi)
    yukleme_suresi = time.time() - baslangic
    bellek_model_sonrasi = bellek_mb()
    print(f"Model yükleme süresi: {yukleme_suresi:.2f} sn")
    print(f"Model yüklenince bellek artışı: {bellek_model_sonrasi - bellek_once:.1f} MB")

    sirketler = veri["sirketler"]
    mesajlar = veri["kullanici_mesajlari"]
    sirket_metinleri = [s["aciklama"] for s in sirketler]

    baslangic = time.time()
    sirket_vektorleri = model.encode(sirket_metinleri, convert_to_tensor=True)
    mesaj_metinleri = [m["mesaj"] for m in mesajlar]
    mesaj_vektorleri = model.encode(mesaj_metinleri, convert_to_tensor=True)
    hesaplama_suresi = time.time() - baslangic
    mesaj_basi_sure_ms = (hesaplama_suresi / len(mesajlar)) * 1000

    dogru_sayisi = 0
    belirsiz_dogru = 0  # "belirsiz" olması gereken mesajları doğru tespit etti mi
    belirsiz_toplam = sum(1 for m in mesajlar if m["beklenen_sektor"] == "belirsiz")

    print(f"\n{'Mesaj':<55} {'Beklenen':<12} {'Bulunan':<12} {'Skor':<8} {'Doğru?'}")
    print("-" * 100)

    for i, mesaj in enumerate(mesajlar):
        skorlar = util.cos_sim(mesaj_vektorleri[i], sirket_vektorleri)[0]
        en_iyi_idx = int(skorlar.argmax())
        en_iyi_skor = float(skorlar[en_iyi_idx])

        if en_iyi_skor < SIMILARITY_ESIK:
            bulunan_sektor = "belirsiz"
        else:
            bulunan_sektor = sirketler[en_iyi_idx]["sektor"]

        dogru = bulunan_sektor == mesaj["beklenen_sektor"]
        dogru_sayisi += int(dogru)
        if mesaj["beklenen_sektor"] == "belirsiz" and dogru:
            belirsiz_dogru += 1

        print(f"{mesaj['mesaj']:<55} {mesaj['beklenen_sektor']:<12} {bulunan_sektor:<12} "
              f"%{en_iyi_skor*100:<6.1f} {'✓' if dogru else '✗'}")

    dogruluk = dogru_sayisi / len(mesajlar) * 100
    bellek_son = bellek_mb()

    print(f"\nGenel doğruluk: {dogru_sayisi}/{len(mesajlar)} (%{dogruluk:.1f})")
    print(f"'Belirsiz' mesajları doğru yakalama: {belirsiz_dogru}/{belirsiz_toplam}")
    print(f"Mesaj başına ortalama süre: {mesaj_basi_sure_ms:.2f} ms")
    print(f"Toplam bellek kullanımı (model + veri): {bellek_son - bellek_once:.1f} MB")

    return {
        "model": model_adi,
        "dogruluk": dogruluk,
        "belirsiz_dogru": belirsiz_dogru,
        "belirsiz_toplam": belirsiz_toplam,
        "yukleme_suresi": yukleme_suresi,
        "mesaj_basi_sure_ms": mesaj_basi_sure_ms,
        "bellek_mb": bellek_son - bellek_once,
        "vektor_boyutu": sirket_vektorleri.shape[1],
    }


def main():
    veri = veri_yukle()
    sonuclar = []

    for isim, model_id in MODELLER.items():
        sonuc = modeli_test_et(model_id, veri)
        sonuclar.append(sonuc)

    print(f"\n\n{'=' * 70}\nÖZET — VERİMLİLİK KARŞILAŞTIRMASI\n{'=' * 70}")
    print(f"{'Model':<25} {'Doğruluk':<12} {'Belirsiz':<12} {'Süre/mesaj':<14} {'Bellek':<10} {'Boyut'}")
    for s in sonuclar:
        print(f"{s['model']:<25} %{s['dogruluk']:<11.1f} "
              f"{s['belirsiz_dogru']}/{s['belirsiz_toplam']:<10} "
              f"{s['mesaj_basi_sure_ms']:<13.2f}ms {s['bellek_mb']:<9.0f}MB {s['vektor_boyutu']}")


if __name__ == "__main__":
    main()
