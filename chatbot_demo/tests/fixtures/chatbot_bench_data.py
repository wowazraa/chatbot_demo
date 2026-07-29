"""
Chatbot-domain benchmark ortak verisi
=====================================
4 sektor + belirsiz. Varsayilan 1000 vaka (20 sert + corpus ornekleri).

    from fixtures.chatbot_bench_data import build_cases, PASSAGES, MODELS
    cases = build_cases(n=1000)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN_JSON = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
AUG_JSON = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

PASSAGES: list[str] = [
    "Hastane bilgi yönetim sistemi (HBYS), poliklinik randevu, teletıp ve eczane stok takibi için sağlık yazılımı.",
    "Otel rezervasyon, check-in/check-out, PNR/bilet ve resort yönetim otomasyonu için turizm yazılımı.",
    "Askeri haberleşme, radar izleme, komuta kontrol ve kriptolu birlik lojistiği için savunma yazılımı.",
    "Üniversite OBS/LMS, öğrenci kayıt, sınav otomasyonu ve uzaktan eğitim platformu için eğitim yazılımı.",
    "Genel kurumsal iş ortaklığı, fiyat teklifi ve demo planlama; belirli bir sektör ürünü yok.",
]

SEKTOR: list[str] = ["sağlık", "turizm", "savunma", "eğitim", "belirsiz"]

_SEKTOR_TO_GOLD = {
    "sağlık": 0,
    "saglik": 0,
    "turizm": 1,
    "savunma": 2,
    "eğitim": 3,
    "egitim": 3,
    "belirsiz": 4,
    "": 4,
}

# 20 sert vaka (negasyon / metafor / capraz / gurultu) — her zaman dahil
HARD_CASES: list[dict] = [
    {"id": "N01", "zorluk": "net", "query": "Hastanemiz için HBYS ve teletıp altyapısı arıyoruz.", "gold": 0, "not": "Net saglik"},
    {"id": "N02", "zorluk": "net", "query": "Otelimizde rezervasyon ve PNR entegrasyonu lazım.", "gold": 1, "not": "Net turizm"},
    {"id": "N03", "zorluk": "net", "query": "Birlik haberleşmesi ve radar izleme yazılımı istiyoruz.", "gold": 2, "not": "Net savunma"},
    {"id": "N04", "zorluk": "net", "query": "Üniversiteye OBS ve LMS kurmak istiyoruz.", "gold": 3, "not": "Net egitim"},
    {"id": "A01", "zorluk": "negasyon", "query": "Sağlık sistemi istemiyoruz, bize turizm rezervasyon yazılımı lazım.", "gold": 1, "not": "saglik reddi -> turizm"},
    {"id": "A02", "zorluk": "negasyon", "query": "Savunma sanayi projesi değil, eğitim otomasyonu ile ilgileniyoruz.", "gold": 3, "not": "savunma reddi -> egitim"},
    {"id": "A03", "zorluk": "negasyon", "query": "Otel yönetimi yerine radar kontrol yazılımı yaptıracağız.", "gold": 2, "not": "turizm reddi -> savunma"},
    {"id": "A04", "zorluk": "negasyon", "query": "LMS kurulumundan vazgeçtik, telemedicine altyapısı talep ediyoruz.", "gold": 0, "not": "egitim reddi -> saglik"},
    {"id": "F01", "zorluk": "metafor", "query": "Sağlıklı bir iş ortaklığı kurmak istiyoruz.", "gold": 4, "not": "saglikli metafor"},
    {"id": "F02", "zorluk": "metafor", "query": "Turistik bir bölgede ofisimiz var, yazılım partneri arıyoruz.", "gold": 4, "not": "konum != turizm"},
    {"id": "F03", "zorluk": "metafor", "query": "Ekibimizi savunan güçlü bir IT altyapısı lazım, sektörümüz belli değil.", "gold": 4, "not": "savunan metafor"},
    {"id": "F04", "zorluk": "metafor", "query": "Personelimizi eğitmek için genel kurumsal eğitim kataloğu bakıyoruz, okul değiliz.", "gold": 4, "not": "IK != egitim sektoru"},
    {"id": "X01", "zorluk": "capraz", "query": "Sağlık turizmi yapan otelimiz için check-in ve oda yönetimi yazılımı arıyoruz.", "gold": 1, "not": "tibbi turizm -> turizm"},
    {"id": "X02", "zorluk": "capraz", "query": "Askeri hastanede poliklinik randevu ve hasta kayıt sistemi kuracağız.", "gold": 0, "not": "askeri hastane -> saglik"},
    {"id": "X03", "zorluk": "capraz", "query": "TSK personeline yönelik uzaktan eğitim ve sınav otomasyonu platformu istiyoruz.", "gold": 3, "not": "TSK ama urun egitim"},
    {"id": "X04", "zorluk": "capraz", "query": "Hastane içi personel LMS'i değil; klinik randevu ve HBYS bakıyoruz.", "gold": 0, "not": "LMS tuzagi -> saglik"},
    {"id": "C01", "zorluk": "gurultu", "query": "Merhaba iyi günler hbys teklifi alabilir miyiz?", "gold": 0, "not": "selam + hbys"},
    {"id": "C02", "zorluk": "gurultu", "query": "obs / lms entegre ogrenci kayit sistemi lazim", "gold": 3, "not": "ASCII egitim"},
    {"id": "C03", "zorluk": "gurultu", "query": "aselsan benzeri radar ve komuta kontrol yazilimi", "gold": 2, "not": "ASCII savunma"},
    {"id": "C04", "zorluk": "gurultu", "query": "pnr bilet otel checkin otomasyonu istiyoruz!!!", "gold": 1, "not": "kisaltma turizm"},
]


def _load_corpus_rows() -> list[dict]:
    path = CLEAN_JSON if CLEAN_JSON.exists() else AUG_JSON
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("kayitlar", [])) if isinstance(raw, dict) else list(raw)


def build_cases(n: int = 1000, seed: int = 42) -> list[dict]:
    """
    n vaka uret: once 20 HARD, kalanini clean/augmented corpus'tan
    sektor-dengeli ornekle (gold = PASSAGES indeksi).
    """
    n = max(1, int(n))
    hard = [dict(c) for c in HARD_CASES]
    if n <= len(hard):
        return hard[:n]

    rows = _load_corpus_rows()
    # sektor -> aday mesajlar
    buckets: dict[int, list[str]] = {i: [] for i in range(5)}
    seen_q = {c["query"].strip().lower() for c in hard}
    for r in rows:
        msg = str(r.get("mesaj") or "").strip()
        if not msg or msg.lower() in seen_q:
            continue
        sek = str(r.get("beklenen_sektor") or "").strip().lower()
        gold = _SEKTOR_TO_GOLD.get(sek, 4)
        buckets[gold].append(msg)
        seen_q.add(msg.lower())

    need = n - len(hard)
    # dengeli cek: her sektorden yaklasik esit
    rng = __import__("random").Random(seed)
    picked: list[dict] = []
    sector_order = [0, 1, 2, 3, 4]
    per = max(1, need // 5)
    for g in sector_order:
        pool = list(buckets[g])
        rng.shuffle(pool)
        take = pool[:per]
        for j, q in enumerate(take):
            picked.append(
                {
                    "id": f"D{g}{j:03d}",
                    "zorluk": "corpus",
                    "query": q,
                    "gold": g,
                    "not": f"corpus->{SEKTOR[g]}",
                }
            )

    # kalan kotayi rastgele doldur
    if len(picked) < need:
        rest_pool: list[tuple[int, str]] = []
        for g, msgs in buckets.items():
            for m in msgs:
                rest_pool.append((g, m))
        rng.shuffle(rest_pool)
        used = {p["query"].lower() for p in picked}
        for g, q in rest_pool:
            if q.lower() in used:
                continue
            picked.append(
                {
                    "id": f"R{len(picked):04d}",
                    "zorluk": "corpus",
                    "query": q,
                    "gold": g,
                    "not": f"corpus->{SEKTOR[g]}",
                }
            )
            used.add(q.lower())
            if len(picked) >= need:
                break

    cases = hard + picked[:need]
    return cases[:n]


# Geriye uyumluluk: eski importlar
CASES: list[dict] = build_cases(1000)

ONNX_QUERY = HARD_CASES[4]["query"]  # A01
ONNX_PASSAGES = PASSAGES[:4]

MODELS = {
    "bge-m3 (bi)": ("BAAI/bge-m3", "bi"),
    "bge-reranker-large": ("BAAI/bge-reranker-large", "cross"),
    "bge-reranker-v2-m3": ("BAAI/bge-reranker-v2-m3", "cross"),
}

RERANKER_ID = "BAAI/bge-reranker-v2-m3"
