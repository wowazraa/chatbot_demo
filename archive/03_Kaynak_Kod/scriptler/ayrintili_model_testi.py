"""
ayrintili_model_testi.py
========================
Tur 4 — Ayrıntılı zorlu sete tüm modelleri sokar ve kırılımlı rapor üretir.

Ölçülenler:
  - Genel doğruluk, belirsiz / tuzak / kısa / parafraz kırılımları
  - Sektör bazlı doğruluk
  - Zorluk tipi bazlı doğruluk
  - En sık karışan sektör çiftleri (confusion)
  - Skor istatistikleri (doğru vs yanlış)
  - Top-1 / Top-2 skor farkı (güven marjı)
  - Eşik taraması (0.40 … 0.70) — hangi eşik daha iyi?
  - Yükleme süresi, ms/mesaj, bellek

Kurulum: pip install sentence-transformers psutil
Çalıştırma: python ayrintili_model_testi.py

İsteğe bağlı: sonuçları JSON olarak kaydetmek için
  python ayrintili_model_testi.py --kaydet
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import psutil
from sentence_transformers import SentenceTransformer, util

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
ESIK_TARAMASI = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
VERI_YOLU = "../veri/ayrintili_zorlu_veri.json"


def veri_yukle(path: str = VERI_YOLU) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def mesajlara_onek_ekle(veri: dict, onek: str = "", sonek: str = "") -> dict:
    """JSON dosyasını değiştirmez; bellekteki mesajların başına/sonuna ekler (deney)."""
    if not onek and not sonek:
        return veri
    kopya = {
        **veri,
        "kullanici_mesajlari": [
            {
                **m,
                "mesaj": f"{onek}{m['mesaj']}{sonek}",
                "mesaj_orijinal": m["mesaj"],
            }
            for m in veri["kullanici_mesajlari"]
        ],
    }
    return kopya


def bellek_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def pct(n: int, d: int) -> float:
    return (n / d * 100.0) if d else 0.0


def tahmin_et(skorlar, sirketler, esik: float) -> tuple[str, float, int, float]:
    """Döner: (bulunan_sektor, top1_skor, top1_idx, top2_skor)."""
    skor_list = [(float(skorlar[i]), i) for i in range(len(skorlar))]
    skor_list.sort(reverse=True)
    top1_skor, top1_idx = skor_list[0]
    top2_skor = skor_list[1][0] if len(skor_list) > 1 else 0.0
    if top1_skor < esik:
        return "belirsiz", top1_skor, top1_idx, top2_skor
    return sirketler[top1_idx]["sektor"], top1_skor, top1_idx, top2_skor


def modeli_test_et(isim: str, model_adi: str, veri: dict) -> dict:
    print(f"\n{'=' * 78}")
    print(f"{isim}")
    print(f"{model_adi}")
    print(f"{'=' * 78}")

    bellek_once = bellek_mb()
    t0 = time.time()
    try:
        model = SentenceTransformer(model_adi)
    except Exception as e:
        print(f"MODEL YÜKLENEMEDİ: {e}")
        return {"isim": isim, "model": model_adi, "hata": str(e)}

    yukleme_suresi = time.time() - t0
    print(f"Yükleme: {yukleme_suresi:.2f} sn | Bellek +{bellek_mb() - bellek_once:.1f} MB")

    sirketler = veri["sirketler"]
    mesajlar = veri["kullanici_mesajlari"]

    t1 = time.time()
    sirket_vec = model.encode([s["aciklama"] for s in sirketler], convert_to_tensor=True)
    mesaj_vec = model.encode([m["mesaj"] for m in mesajlar], convert_to_tensor=True)
    encode_suresi = time.time() - t1
    ms_mesaj = (encode_suresi / len(mesajlar)) * 1000

    detaylar = []
    for i, mesaj in enumerate(mesajlar):
        skorlar = util.cos_sim(mesaj_vec[i], sirket_vec)[0]
        bulunan, top1, top1_idx, top2 = tahmin_et(skorlar, sirketler, SIMILARITY_ESIK)
        beklenen = mesaj["beklenen_sektor"]
        dogru = bulunan == beklenen
        detaylar.append(
            {
                "id": mesaj["id"],
                "mesaj": mesaj["mesaj"],
                "beklenen": beklenen,
                "bulunan": bulunan,
                "dogru": dogru,
                "zorluk": mesaj.get("zorluk", "?"),
                "tuzak_tipi": mesaj.get("tuzak_tipi"),
                "top1_skor": round(top1, 4),
                "top2_skor": round(top2, 4),
                "marj": round(top1 - top2, 4),
                "en_yakin_sirket": sirketler[top1_idx]["ad"],
            }
        )

    # --- Genel ---
    toplam = len(detaylar)
    dogru_n = sum(1 for d in detaylar if d["dogru"])

    def kirilim(filtre):
        alt = [d for d in detaylar if filtre(d)]
        d_n = sum(1 for d in alt if d["dogru"])
        return {"n": len(alt), "dogru": d_n, "yuzde": round(pct(d_n, len(alt)), 1)}

    zorluk_kirilim = {}
    for z in sorted({d["zorluk"] for d in detaylar}):
        zorluk_kirilim[z] = kirilim(lambda d, zz=z: d["zorluk"] == zz)

    sektor_kirilim = {}
    for s in sorted({d["beklenen"] for d in detaylar if d["beklenen"] != "belirsiz"}):
        sektor_kirilim[s] = kirilim(lambda d, ss=s: d["beklenen"] == ss)

    belirsiz = kirilim(lambda d: d["beklenen"] == "belirsiz")
    tuzak = kirilim(lambda d: d["zorluk"] == "tuzak")
    kisa = kirilim(lambda d: d["zorluk"] == "kisa")
    parafraz = kirilim(lambda d: d["zorluk"] == "parafraz")
    cok_anlamli = kirilim(lambda d: d["zorluk"] == "cok_anlamli")

    # --- Confusion: yanlışlarda beklenen -> bulunan ---
    yanlis_ciftler = Counter()
    for d in detaylar:
        if not d["dogru"]:
            yanlis_ciftler[(d["beklenen"], d["bulunan"])] += 1
    en_sik_hatalar = [
        {"beklenen": a, "bulunan": b, "adet": c}
        for (a, b), c in yanlis_ciftler.most_common(10)
    ]

    # --- Skor istatistikleri ---
    def skor_stat(alt):
        if not alt:
            return {"n": 0, "ortalama": 0, "min": 0, "max": 0, "marj_ort": 0}
        skorlar_ = [d["top1_skor"] for d in alt]
        marjlar = [d["marj"] for d in alt]
        return {
            "n": len(alt),
            "ortalama": round(sum(skorlar_) / len(skorlar_), 3),
            "min": round(min(skorlar_), 3),
            "max": round(max(skorlar_), 3),
            "marj_ort": round(sum(marjlar) / len(marjlar), 3),
        }

    skor_dogru = skor_stat([d for d in detaylar if d["dogru"] and d["beklenen"] != "belirsiz"])
    skor_yanlis = skor_stat([d for d in detaylar if not d["dogru"]])
    skor_belirsiz_beklenen = skor_stat([d for d in detaylar if d["beklenen"] == "belirsiz"])

    # --- Eşik taraması (aynı embedding'ler üzerinde) ---
    esik_sonuclari = []
    for esik in ESIK_TARAMASI:
        d_n = 0
        b_dogru = 0
        b_toplam = belirsiz["n"]
        for i, mesaj in enumerate(mesajlar):
            skorlar = util.cos_sim(mesaj_vec[i], sirket_vec)[0]
            bulunan, _, _, _ = tahmin_et(skorlar, sirketler, esik)
            if bulunan == mesaj["beklenen_sektor"]:
                d_n += 1
                if mesaj["beklenen_sektor"] == "belirsiz":
                    b_dogru += 1
        esik_sonuclari.append(
            {
                "esik": esik,
                "dogruluk": round(pct(d_n, toplam), 1),
                "dogru": d_n,
                "belirsiz_yakalama": f"{b_dogru}/{b_toplam}",
            }
        )

    # Konsol çıktısı
    print(f"\n--- GENEL ---")
    print(f"Doğruluk: {dogru_n}/{toplam} (%{pct(dogru_n, toplam):.1f})")
    print(f"Belirsiz yakalama: {belirsiz['dogru']}/{belirsiz['n']} (%{belirsiz['yuzde']})")
    print(f"Tuzak yakalama: {tuzak['dogru']}/{tuzak['n']} (%{tuzak['yuzde']})")
    print(f"Parafraz: %{parafraz['yuzde']} | Kısa: %{kisa['yuzde']} | Çok anlamlı: %{cok_anlamli['yuzde']}")
    print(f"Süre/mesaj: {ms_mesaj:.2f} ms | Encode: {encode_suresi:.2f} sn")
    print(f"Bellek artışı: {bellek_mb() - bellek_once:.1f} MB | Vektör: {sirket_vec.shape[1]}")

    print(f"\n--- ZORLUK KIRILIMI ---")
    for z, s in zorluk_kirilim.items():
        print(f"  {z:<14} {s['dogru']}/{s['n']:<4} (%{s['yuzde']})")

    print(f"\n--- SEKTÖR KIRILIMI (beklenen ≠ belirsiz) ---")
    for s, v in sektor_kirilim.items():
        print(f"  {s:<18} {v['dogru']}/{v['n']:<3} (%{v['yuzde']})")

    print(f"\n--- SKOR İSTATİSTİKLERİ (top-1 cosine) ---")
    print(f"  Doğru eşleşmeler : ort={skor_dogru['ortalama']} min={skor_dogru['min']} "
          f"max={skor_dogru['max']} marj_ort={skor_dogru['marj_ort']}")
    print(f"  Yanlış eşleşmeler: ort={skor_yanlis['ortalama']} min={skor_yanlis['min']} "
          f"max={skor_yanlis['max']} marj_ort={skor_yanlis['marj_ort']}")
    print(f"  Belirsiz beklenen: ort={skor_belirsiz_beklenen['ortalama']} "
          f"(eşik altı kalmalı)")

    print(f"\n--- EN SIK HATALAR (beklenen → bulunan) ---")
    if not en_sik_hatalar:
        print("  (yok)")
    for h in en_sik_hatalar:
        print(f"  {h['beklenen']} → {h['bulunan']}: {h['adet']}")

    print(f"\n--- EŞİK TARAMASI ---")
    print(f"  {'Eşik':<8} {'Doğruluk':<12} {'Belirsiz'}")
    for e in esik_sonuclari:
        isaret = " <-- mevcut" if e["esik"] == SIMILARITY_ESIK else ""
        print(f"  {e['esik']:<8} %{e['dogruluk']:<11} {e['belirsiz_yakalama']}{isaret}")

    print(f"\n--- YANLIŞ ÖRNEKLER (ilk 8) ---")
    yanlislar = [d for d in detaylar if not d["dogru"]]
    for d in yanlislar[:8]:
        print(
            f"  [{d['zorluk']}] {d['mesaj'][:55]}"
            f"\n      beklenen={d['beklenen']} bulunan={d['bulunan']} "
            f"skor={d['top1_skor']} marj={d['marj']} ({d['en_yakin_sirket']})"
        )
    if len(yanlislar) > 8:
        print(f"  ... +{len(yanlislar) - 8} yanlış daha")

    del model

    return {
        "isim": isim,
        "model": model_adi,
        "hata": None,
        "yukleme_suresi": round(yukleme_suresi, 2),
        "ms_mesaj": round(ms_mesaj, 2),
        "bellek_mb": round(bellek_mb() - bellek_once, 1),
        "vektor_boyutu": int(sirket_vec.shape[1]),
        "genel": {
            "dogru": dogru_n,
            "toplam": toplam,
            "dogruluk": round(pct(dogru_n, toplam), 1),
            "belirsiz": belirsiz,
            "tuzak": tuzak,
            "parafraz": parafraz,
            "kisa": kisa,
            "cok_anlamli": cok_anlamli,
        },
        "zorluk_kirilim": zorluk_kirilim,
        "sektor_kirilim": sektor_kirilim,
        "skor_istatistik": {
            "dogru": skor_dogru,
            "yanlis": skor_yanlis,
            "belirsiz_beklenen": skor_belirsiz_beklenen,
        },
        "en_sik_hatalar": en_sik_hatalar,
        "esik_taramasi": esik_sonuclari,
        "detaylar": detaylar,
    }


def ozet_tablo(sonuclar: list[dict]) -> None:
    print(f"\n\n{'=' * 100}")
    print("ÖZET TABLO — TUR 4 AYRINTILI KARŞILAŞTIRMA")
    print(f"{'=' * 100}")
    print(
        f"{'Model':<20} {'Doğruluk':<14} {'Belirsiz':<12} {'Tuzak':<12} "
        f"{'Parafraz':<10} {'ms':<10} {'MB':<8} {'Boyut'}"
    )
    print("-" * 100)
    for s in sonuclar:
        if s.get("hata"):
            print(f"{s['isim']:<20} HATA: {s['hata'][:60]}")
            continue
        g = s["genel"]
        print(
            f"{s['isim']:<20} {g['dogru']}/{g['toplam']} (%{g['dogruluk']:<5.1f}) "
            f"{g['belirsiz']['dogru']}/{g['belirsiz']['n']:<10} "
            f"{g['tuzak']['dogru']}/{g['tuzak']['n']:<10} "
            f"%{g['parafraz']['yuzde']:<9.1f} "
            f"{s['ms_mesaj']:<10.2f} {s['bellek_mb']:<8.0f} {s['vektor_boyutu']}"
        )

    basarili = [s for s in sonuclar if not s.get("hata")]
    if not basarili:
        return

    en_iyi_dog = max(basarili, key=lambda x: x["genel"]["dogruluk"])
    en_hizli = min(basarili, key=lambda x: x["ms_mesaj"])
    en_iyi_tuzak = max(basarili, key=lambda x: x["genel"]["tuzak"]["yuzde"])
    print(f"\nEn yüksek doğruluk : {en_iyi_dog['isim']} (%{en_iyi_dog['genel']['dogruluk']})")
    print(f"En iyi tuzak skoru : {en_iyi_tuzak['isim']} "
          f"(%{en_iyi_tuzak['genel']['tuzak']['yuzde']})")
    print(f"En hızlı           : {en_hizli['isim']} ({en_hizli['ms_mesaj']} ms/mesaj)")

    print(f"\n--- EŞİK ÖNERİSİ (modellere göre %{SIMILARITY_ESIK} bandı) ---")
    for s in basarili:
        en_iyi_esik = max(s["esik_taramasi"], key=lambda e: e["dogruluk"])
        print(
            f"  {s['isim']:<20} mevcut 0.50 → %{s['genel']['dogruluk']} | "
            f"bu sette en iyi eşik {en_iyi_esik['esik']} → %{en_iyi_esik['dogruluk']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Tur 4 ayrıntılı model testi")
    parser.add_argument(
        "--kaydet",
        action="store_true",
        help="Sonuçları ../veri/ayrintili_test_sonuclari.json olarak kaydet",
    )
    parser.add_argument(
        "--sadece",
        nargs="*",
        default=None,
        help="Sadece bu model anahtarlarını çalıştır (örn: --sadece \"MiniLM (384)\")",
    )
    parser.add_argument(
        "--onek",
        type=str,
        default=None,
        help='Deney: her mesajın başına ekle (JSON değişmez). Örn: --onek "Merhaba, "',
    )
    parser.add_argument(
        "--sonek",
        type=str,
        default=None,
        help='Deney: her mesajın sonuna ekle (JSON değişmez). Örn: --sonek " Teşekkürler."',
    )
    args = parser.parse_args()

    veri = veri_yukle()
    onek = args.onek or ""
    sonek = args.sonek or ""
    if onek or sonek:
        veri = mesajlara_onek_ekle(veri, onek=onek, sonek=sonek)

    sektorler = sorted({s["sektor"] for s in veri["sirketler"]})
    zorluklar = Counter(m.get("zorluk") for m in veri["kullanici_mesajlari"])

    print("TUR 4 — AYRINTILI ZORLU TEST")
    print(f"Veri        : {VERI_YOLU}")
    print(f"Önek deneyi : {args.onek!r}" if args.onek else "Önek deneyi : yok")
    print(f"Sonek deneyi: {args.sonek!r}" if args.sonek else "Sonek deneyi: yok")
    print(f"Şirket      : {len(veri['sirketler'])}")
    print(f"Mesaj       : {len(veri['kullanici_mesajlari'])}")
    print(f"Sektör      : {len(sektorler)} -> {', '.join(sektorler)}")
    print(f"Zorluk dağılımı: {dict(zorluklar)}")
    print(f"Eşik        : {SIMILARITY_ESIK}")
    print(f"Eşik tarama : {ESIK_TARAMASI}")
    if onek or sonek:
        ornek = veri["kullanici_mesajlari"][0]["mesaj"]
        print(f"Örnek mesaj : {ornek[:80]}...")

    modeller = ADAY_MODELLER
    if args.sadece:
        modeller = {k: v for k, v in ADAY_MODELLER.items() if k in args.sadece}
        if not modeller:
            raise SystemExit(f"--sadece eşleşmedi. Seçenekler: {list(ADAY_MODELLER)}")

    sonuclar = []
    for isim, model_id in modeller.items():
        sonuclar.append(modeli_test_et(isim, model_id, veri))

    ozet_tablo(sonuclar)

    if args.kaydet:
        if onek or sonek:
            out_path = "../veri/ayrintili_test_sonuclari_onek_sonek_deney.json"
        else:
            out_path = "../veri/ayrintili_test_sonuclari.json"
        paket = {
            "zaman": datetime.now(timezone.utc).isoformat(),
            "veri": VERI_YOLU,
            "onek": args.onek,
            "sonek": args.sonek,
            "esik": SIMILARITY_ESIK,
            "sonuclar": sonuclar,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(paket, f, ensure_ascii=False, indent=2)
        print(f"\nSonuçlar kaydedildi: {out_path}")


if __name__ == "__main__":
    main()
