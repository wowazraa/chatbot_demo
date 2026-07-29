"""
Similarity model karşılaştırma scripti.
Kurulum: pip install sentence-transformers
Çalıştırma: python model_karsilastirma.py

Bu script, ornek_veri.json içindeki şirket açıklamaları ile kullanıcı
mesajlarını iki farklı embedding modeliyle (MiniLM ve BGE-M3) vektöre
çevirir, cosine similarity hesaplar ve her mesaj için en yakın şirketi
bulur. İki modelin doğruluğunu (beklenen_sektor ile karşılaştırarak)
ve hızını raporlar.
"""

import json
import time
from sentence_transformers import SentenceTransformer, util

MODELLER = {
    "MiniLM (384 boyut, hızlı/hafif)": "paraphrase-multilingual-MiniLM-L12-v2",
    "BGE-M3 (1024 boyut, yüksek doğruluk)": "BAAI/bge-m3",
}


def veri_yukle(path="../veri/ornek_veri.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def modeli_test_et(model_adi, veri):
    print(f"\n{'=' * 60}\nModel: {model_adi}\n{'=' * 60}")

    baslangic = time.time()
    model = SentenceTransformer(model_adi)
    yukleme_suresi = time.time() - baslangic
    print(f"Model yükleme süresi: {yukleme_suresi:.2f} sn")

    sirketler = veri["sirketler"]
    mesajlar = veri["kullanici_mesajlari"]

    sirket_metinleri = [s["aciklama"] for s in sirketler]

    baslangic = time.time()
    sirket_vektorleri = model.encode(sirket_metinleri, convert_to_tensor=True)
    mesaj_metinleri = [m["mesaj"] for m in mesajlar]
    mesaj_vektorleri = model.encode(mesaj_metinleri, convert_to_tensor=True)
    hesaplama_suresi = time.time() - baslangic

    dogru_sayisi = 0
    print(f"\n{'Mesaj':<50} {'Bulunan Sektör':<15} {'Skor':<8} {'Doğru mu?'}")
    print("-" * 90)

    for i, mesaj in enumerate(mesajlar):
        skorlar = util.cos_sim(mesaj_vektorleri[i], sirket_vektorleri)[0]
        en_iyi_idx = int(skorlar.argmax())
        en_iyi_skor = float(skorlar[en_iyi_idx])
        bulunan_sirket = sirketler[en_iyi_idx]
        bulunan_sektor = bulunan_sirket["sektor"]
        dogru = bulunan_sektor == mesaj["beklenen_sektor"]
        dogru_sayisi += int(dogru)

        print(f"{mesaj['mesaj']:<50} {bulunan_sektor:<15} %{en_iyi_skor*100:<6.1f} {'✓' if dogru else '✗'}")

    dogruluk = dogru_sayisi / len(mesajlar) * 100
    print(f"\nDoğruluk: {dogru_sayisi}/{len(mesajlar)} (%{dogruluk:.1f})")
    print(f"Embedding hesaplama süresi: {hesaplama_suresi:.2f} sn")
    print(f"Vektör boyutu: {sirket_vektorleri.shape[1]}")

    return {
        "model": model_adi,
        "dogruluk": dogruluk,
        "yukleme_suresi": yukleme_suresi,
        "hesaplama_suresi": hesaplama_suresi,
        "vektor_boyutu": sirket_vektorleri.shape[1],
    }


def main():
    veri = veri_yukle()
    sonuclar = []

    for isim, model_id in MODELLER.items():
        sonuc = modeli_test_et(model_id, veri)
        sonuclar.append(sonuc)

    print(f"\n\n{'=' * 60}\nÖZET KARŞILAŞTIRMA\n{'=' * 60}")
    for s in sonuclar:
        print(f"{s['model']}")
        print(f"  Doğruluk: %{s['dogruluk']:.1f} | Vektör boyutu: {s['vektor_boyutu']} "
              f"| Hesaplama süresi: {s['hesaplama_suresi']:.2f} sn")


if __name__ == "__main__":
    main()
