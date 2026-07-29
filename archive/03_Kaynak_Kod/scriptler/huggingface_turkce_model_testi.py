"""
huggingface_turkce_model_testi.py
=================================
Tur 3 — Çok zorlu veri seti üzerinde TÜM aday modelleri karşılaştırır:
  - MiniLM (nihai seçim)
  - BGE-M3
  - Turkish-E5-Large, TR-MTEB, BERTurk NLI-STSb

Kurulum: pip install sentence-transformers psutil
Çalıştırma: python huggingface_turkce_model_testi.py

Veri (varsayılan): ../veri/cok_zorlu_veri.json
Daha ayrıntılı Tur 4 için: python ayrintili_model_testi.py
"""

import json
import os
import time

import psutil
from sentence_transformers import SentenceTransformer, util

# Tüm adaylar: rapordaki modeller + Türkçe HF modelleri
ADAY_MODELLER = {
    "MiniLM (384)": "paraphrase-multilingual-MiniLM-L12-v2",
    "BGE-M3 (1024)": "BAAI/bge-m3",
    "Turkish-E5-Large": "ytu-ce-cosmos/turkish-e5-large",
    "TR-MTEB Fine-Tuned": "trmteb/turkish-embedding-model-fine-tuned",
    "BERTurk NLI-STSb": "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr",
    # https://huggingface.co/nezahatkorkmaz/turkce-embedding-bge-m3
    "TR-BGE-M3 (nezahat)": "nezahatkorkmaz/turkce-embedding-bge-m3",
}

SIMILARITY_ESIK = 0.50
VERI_YOLU = "../veri/cok_zorlu_veri.json"


def veri_yukle(path=VERI_YOLU):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def bellek_mb():
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024 * 1024)


def modeli_test_et(isim, model_adi, veri):
    print(f"\n{'=' * 70}\n{isim}\n{model_adi}\n{'=' * 70}")

    bellek_once = bellek_mb()
    baslangic = time.time()
    try:
        model = SentenceTransformer(model_adi)
    except Exception as e:
        print(f"MODEL YÜKLENEMEDİ: {e}")
        return {
            "isim": isim,
            "model": model_adi,
            "hata": str(e),
            "dogruluk": 0.0,
            "dogru": 0,
            "toplam": 0,
            "belirsiz_dogru": 0,
            "belirsiz_toplam": 0,
            "tuzak_dogru": 0,
            "tuzak_toplam": 0,
            "yukleme_suresi": 0.0,
            "mesaj_basi_sure_ms": 0.0,
            "bellek_mb": 0.0,
            "vektor_boyutu": 0,
        }

    yukleme_suresi = time.time() - baslangic
    print(f"Yükleme: {yukleme_suresi:.2f} sn | Bellek +{bellek_mb() - bellek_once:.1f} MB")

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
    belirsiz_dogru = 0
    belirsiz_toplam = sum(1 for m in mesajlar if m["beklenen_sektor"] == "belirsiz")
    tuzak_dogru = 0
    tuzak_toplam = sum(1 for m in mesajlar if str(m.get("zorluk", "")).startswith("tuzak"))

    print(f"\n{'Mesaj':<60} {'Beklenen':<12} {'Bulunan':<12} {'Skor':<8} {'?'}")
    print("-" * 105)

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
        if str(mesaj.get("zorluk", "")).startswith("tuzak") and dogru:
            tuzak_dogru += 1

        kisa = mesaj["mesaj"][:58]
        print(
            f"{kisa:<60} {mesaj['beklenen_sektor']:<12} {bulunan_sektor:<12} "
            f"%{en_iyi_skor * 100:<6.1f} {'✓' if dogru else '✗'}"
        )

    dogruluk = dogru_sayisi / len(mesajlar) * 100
    bellek_son = bellek_mb()

    print(f"\nDoğruluk: {dogru_sayisi}/{len(mesajlar)} (%{dogruluk:.1f})")
    print(f"Belirsiz yakalama: {belirsiz_dogru}/{belirsiz_toplam}")
    print(f"Tuzak mesaj yakalama: {tuzak_dogru}/{tuzak_toplam}")
    print(f"Süre/mesaj: {mesaj_basi_sure_ms:.2f} ms | Bellek: {bellek_son - bellek_once:.1f} MB")

    # Model nesnesini bırak (sonraki model için bellek)
    del model

    return {
        "isim": isim,
        "model": model_adi,
        "hata": None,
        "dogruluk": dogruluk,
        "dogru": dogru_sayisi,
        "toplam": len(mesajlar),
        "belirsiz_dogru": belirsiz_dogru,
        "belirsiz_toplam": belirsiz_toplam,
        "tuzak_dogru": tuzak_dogru,
        "tuzak_toplam": tuzak_toplam,
        "yukleme_suresi": yukleme_suresi,
        "mesaj_basi_sure_ms": mesaj_basi_sure_ms,
        "bellek_mb": bellek_son - bellek_once,
        "vektor_boyutu": int(sirket_vektorleri.shape[1]),
    }


def main():
    veri = veri_yukle()
    print(f"Veri: {VERI_YOLU}")
    print(f"Şirket: {len(veri['sirketler'])} | Mesaj: {len(veri['kullanici_mesajlari'])}")
    print(f"Eşik: {SIMILARITY_ESIK}")
    print(f"Model sayısı: {len(ADAY_MODELLER)}")

    sonuclar = []
    for isim, model_id in ADAY_MODELLER.items():
        sonuclar.append(modeli_test_et(isim, model_id, veri))

    print(f"\n\n{'=' * 90}")
    print("ÖZET — TUR 3 ÇOK ZORLU KARŞILAŞTIRMA (MiniLM + BGE-M3 + Türkçe HF)")
    print(f"{'=' * 90}")
    print(
        f"{'Model':<22} {'Doğruluk':<14} {'Belirsiz':<12} {'Tuzak':<12} "
        f"{'ms/mesaj':<12} {'Bellek':<10} {'Boyut'}"
    )
    print("-" * 90)
    for s in sonuclar:
        if s.get("hata"):
            print(f"{s['isim']:<22} HATA: {s['hata'][:50]}")
            continue
        print(
            f"{s['isim']:<22} {s['dogru']}/{s['toplam']} (%{s['dogruluk']:<5.1f}) "
            f"{s['belirsiz_dogru']}/{s['belirsiz_toplam']:<10} "
            f"{s['tuzak_dogru']}/{s['tuzak_toplam']:<10} "
            f"{s['mesaj_basi_sure_ms']:<11.2f} {s['bellek_mb']:<9.0f}MB {s['vektor_boyutu']}"
        )

    basarili = [s for s in sonuclar if not s.get("hata")]
    if basarili:
        en_iyi = max(basarili, key=lambda x: (x["dogruluk"], -x["mesaj_basi_sure_ms"]))
        print(f"\nBu sette en iyi denge (doğruluk öncelikli): {en_iyi['isim']}")


if __name__ == "__main__":
    main()
