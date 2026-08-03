"""
BGE-M3 Embedding Index Builder
================================
Bu script'i SADECE BİR KEZ çalıştırın (veya veri seti güncellenince tekrar).

Yaptığı:
  1) data/processed/chatbot_dataset_augmented.json'u okur
  2) BGE-M3 modelini indirir/yükler (~2.3GB, bir kez)
  3) Tüm kayıtları batch halinde embed eder
  4) data/processed/embeddings.npz + index_meta.json'a kaydeder

Çalıştırma:
    python scripts/build_index.py

Seçenekler:
    python scripts/build_index.py --raw          # artırılmış yerine ham veriyi kullan
    python scripts/build_index.py --batch 32     # batch boyutu (bellek kısıtlıysa)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.embedder import BGEEmbedder

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
RAW_FILE       = ROOT / "data" / "raw"       / "chatbot_dataset.json"
PROCESSED_FILE = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"
INDEX_DIR      = ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Intent Kodu Eşleme Tablosu
# JSON'daki ham Türkçe sektör etiketini → DB-uyumlu intent koduna dönüştürür.
# Bu eşleme olmadan downstream migration script'i [null] üretir.
# ---------------------------------------------------------------------------
SEKTOR_TO_INTENT: dict[str, str] = {
    # Birincil etiketler (ham JSON → DB intent kodu)
    "turizm":   "tourism_hotel",
    "saglik":   "health_appointment",
    "egitim":   "education_enrollment",
    "bilisim":  "bilisim_integration",
    "eglence":  "eglence_streaming",
    # OOD ve belirsiz durumlar — DB tarafında özel işlenir
    "ood":      "ood",
    "belirsiz": "ood",
}

# Varyant destek eşlemesi: Türkçe karakterli versiyonlar (data_augmented.py
# AUGMENTATION_TARGETS anahtarlarından üretilenler için güvenlik ağı)
_SEKTOR_NORMALIZE: dict[str, str] = {
    # Türkçe karakterli -> ASCII normalleştirilmiş
    "sağlık":  "saglik",
    "eğitim":  "egitim",
    "turizm":  "turizm",   # zaten ASCII
    "bilişim": "bilisim",
    "eğlence": "eglence",
    "ood":     "ood",
    "belirsiz":"belirsiz",
}


def resolve_intent(raw_sektor: str | None) -> str:
    """
    Ham sektör etiketini DB-uyumlu intent koduna dönüştürür.

    Adımlar:
      1) Türkçe karakterli versiyonu ASCII'ye normalize et
      2) Eşleme tablosunda ara
      3) Eşleme bulunamazsa 'ood' döndür ve uyarı bas

    UTF-8 güvenli: giriş string'i aynen kullanılır,
    encoding dönüşümü yoktur.
    """
    if not raw_sektor:
        return "ood"

    normalized = _SEKTOR_NORMALIZE.get(raw_sektor.strip(), raw_sektor.strip())
    intent = SEKTOR_TO_INTENT.get(normalized)

    if intent is None:
        print(
            f"  [UYARI] Bilinmeyen sektör etiketi: '{raw_sektor}' → 'ood' atandı. "
            f"SEKTOR_TO_INTENT tablosunu güncelleyin.",
            file=sys.stderr,
        )
        return "ood"

    return intent


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------
def load_records(use_raw: bool = False) -> list[dict]:
    path = RAW_FILE if use_raw else PROCESSED_FILE
    if not path.exists():
        print(f"[!] Dosya bulunamadı: {path}")
        if not use_raw:
            print("    Önce çalıştırın: python src/data_augmented.py")
        sys.exit(1)

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    recs = data.get("kayitlar", data) if isinstance(data, dict) else data
    print(f"[+] {len(recs)} kayıt yüklendi: {path.name}")
    return recs


# ---------------------------------------------------------------------------
# Ana builder
# ---------------------------------------------------------------------------
def build(use_raw: bool = False, batch_size: int = 64) -> None:
    print("=" * 60)
    print("  BGE-M3 Embedding Index Builder")
    print("=" * 60)

    records = load_records(use_raw)

    # Metin ve metadata ayır
    texts: list[str] = []
    meta:  list[dict] = []

    msg_fields = ("mesaj", "message", "text", "input")

    # Intent kodu istatistiği (tanılama için)
    intent_counter: dict[str, int] = {}
    unknown_sektors: set[str] = set()

    for rec in records:
        msg = ""
        for f in msg_fields:
            if f in rec and isinstance(rec[f], str):
                msg = rec[f]
                break
        if not msg:
            continue

        # Ham sektör etiketini al — her iki olası typo'yu da destekle
        raw_sektor = rec.get(
            "beklenen_sektor",
            rec.get("beklened_sektor", "belirsiz"),  # typo koruması
        )

        # ----------------------------------------------------------------
        # KRİTİK: Ham Türkçe etiket → DB-uyumlu intent kodu dönüşümü
        # Bu adım olmadan downstream migration null üretir.
        # ----------------------------------------------------------------
        intent_code = resolve_intent(raw_sektor)

        if intent_code == "ood" and raw_sektor not in ("ood", "belirsiz", None, ""):
            unknown_sektors.add(raw_sektor)

        intent_counter[intent_code] = intent_counter.get(intent_code, 0) + 1

        texts.append(msg)
        meta.append({
            "id":              rec.get("id"),
            "source_id":       rec.get("source_id"),
            # Orijinal ham etiket (hata ayıklama için saklanır)
            "beklenen_sektor": raw_sektor,
            # DB-uyumlu intent kodu — downstream migration bu alanı kullanır
            "intent_code":     intent_code,
            "beklenen_mod":    rec.get("beklenen_mod",    rec.get("beklened_mod",    "K1")),
            "lang":            rec.get("lang", "tr"),
            "zorluk":          rec.get("zorluk", ""),
            "varyant":         rec.get("varyant", "duz"),
        })

    print(f"[+] Embed edilecek: {len(texts)} metin")
    print()

    # Intent dağılımı özeti
    print("--- Intent Kodu Dağılımı ---")
    for code, count in sorted(intent_counter.items(), key=lambda x: -x[1]):
        print(f"  {code:<30} {count:>5}")
    if unknown_sektors:
        print(f"\n  [UYARI] Eşlenemeyen sektörler: {sorted(unknown_sektors)}")
    print()

    embedder = BGEEmbedder()
    t0 = time.time()

    embedder.build_index(texts, meta, show_progress=True)

    elapsed = time.time() - t0
    print(f"\n[+] Embedding tamamlandı: {elapsed:.1f}s")

    embedder.save_index(INDEX_DIR)
    print(f"[+] Index kaydedildi -> {INDEX_DIR}")

    # Hızlı doğrulama
    print("\n--- Hızlı Test ---")
    test_queries = [
        "hastane yönetim sistemi",
        "We need a hotel booking platform",
        "military communication software",
        "online eğitim platformu",
        "fiyat teklifi",
    ]
    for q in test_queries:
        res = embedder.find_top_k(q, k=1)
        if res:
            r = res[0]
            print(
                f"  '{q[:45]}'\n"
                f"    -> [{r.metadata['intent_code']:<25}] {r.score:.4f} | {r.text[:50]}"
            )
    print("\n[+] Index build tamamlandı!")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BGE-M3 Index Builder")
    parser.add_argument("--raw",   action="store_true", help="Artırılmış yerine ham veriyi kullan")
    parser.add_argument("--batch", type=int, default=64, help="Batch boyutu (varsayılan: 64)")
    args = parser.parse_args()

    build(use_raw=args.raw, batch_size=args.batch)
