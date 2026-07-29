# -*- coding: utf-8 -*-
"""
CPB 3-Katmanlı Stres Testi
==========================
Motor koduna DOKUNULMAZ. Sadece ölçüm + centroid güven skoru logu.

Kullanım:
    python tests/stress_test_cpb.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot  # noqa: E402

# Test-only prototipler (motor SECTOR_CENTROID_PROTOTYPES'a dokunulmaz)
# → her sektör için Confidence Score tablosu basmak için
LOG_PROTOTYPES: dict[str, tuple[str, ...]] = {
    "savunma": (
        "askeri savunma sanayii komuta kontrol radar birlik muharebe nato",
        "military defense radar command and control combat",
    ),
    "lojistik": (
        "lojistik depo palet kamyon filo sevkiyat rota optimizasyonu tedarik zinciri",
        "logistics warehouse truck fleet routing supply chain",
    ),
    "ticari": (
        "ticari işletme satış sipariş müşteri lojistik depo operasyon",
        "commercial business sales logistics warehouse operations",
    ),
    "bilişim": (
        "yazılım kod dokümantasyon debug API geliştirme bilgi teknolojileri",
        "software code documentation debugging programming IT systems",
    ),
    "sağlık": (
        "hastane klinik poliklinik teletıp hasta randevu sağlık otomasyonu",
        "hospital clinic healthcare medical patient scheduling",
    ),
    "gida": (
        "gıda tarım dondurma limonata yiyecek içecek sıcak hava",
        "food agriculture ice cream lemonade drink snack weather",
    ),
}


@dataclass
class Layer:
    id: str
    baslik: str
    girdi: str
    beklenen: list[str]
    yasak: list[str] = field(default_factory=list)
    fb_zorunlu: bool = False


LAYERS: list[Layer] = [
    Layer(
        id="L1_cross_sector",
        baslik="Katman 1 — Cross-Sector Ambiguity",
        girdi=(
            "Kargo uçaklarımızın lojistik rotalarını, savunma sistemleri olan "
            "radar kapsama alanlarına göre düzenlememiz gerekiyor."
        ),
        beklenen=["lojistik"],
        yasak=["savunma"],
    ),
    Layer(
        id="L2_adversarial_leet",
        baslik="Katman 2 — Adversarial Leet-Speak",
        girdi=(
            "S!stemler!m!zdeki 3rg0n0m!k hataları gidermek için "
            "(sağlık/hastane değil!) kod dökümanı istiyorum."
        ),
        beklenen=["bilişim"],
        yasak=["sağlık"],
    ),
    Layer(
        id="L3_null_threshold",
        baslik="Katman 3 — The Null-Threshold Test",
        girdi="Hava çok sıcak, dondurma mı yesek yoksa limonata mı?",
        beklenen=["belirsiz"],
        yasak=["sağlık", "turizm", "savunma", "lojistik", "finans", "e_ticaret"],
        fb_zorunlu=True,
    ),
]


def _confidence_table(bot: Chatbot, text: str) -> dict[str, float]:
    """Sorgu ↔ sektör prototip centroid cosine (sadece test logu)."""
    emb = bot._get_embedder()
    if emb is None or not emb.is_ready():
        return {}
    import numpy as np

    q = emb.encode_dense([text])[0]
    scores: dict[str, float] = {}
    for sektor, protos in LOG_PROTOTYPES.items():
        mats = emb.encode_dense(list(protos))
        c = mats.mean(axis=0)
        n = float(np.linalg.norm(c))
        if n > 1e-12:
            c = c / n
        scores[sektor] = round(float(emb.cosine_sim(q, c)), 4)
    return scores


def _fmt_table(scores: dict[str, float]) -> str:
    if not scores:
        return "(embedder yok)"
    parts = [f"{k.capitalize()}: {v:.2f}" for k, v in sorted(scores.items(), key=lambda x: -x[1])]
    return ", ".join(parts)


def evaluate(y, layer: Layer) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if y.sektor in layer.yasak:
        reasons.append(f"YASAK sektör: {y.sektor}")
    if layer.beklenen and y.sektor not in layer.beklenen:
        reasons.append(f"Beklenen {layer.beklenen}, gelen '{y.sektor}'")
    if layer.fb_zorunlu and y.sektor != "belirsiz" and y.mod != "FB":
        reasons.append(f"FB zorunlu ama sektor={y.sektor} mod={y.mod}")
    # L1: lojistik korunmalı
    if layer.id == "L1_cross_sector":
        if "lojistik" not in (y.temiz_sorgu or "").lower():
            reasons.append("Rewriter 'lojistik' terimini sildi")
        if y.sektor != "lojistik":
            reasons.append("Lojistik > Savunma bekleniyordu")
    # L2: negasyon koruması + conf≥0.70
    if layer.id == "L2_adversarial_leet":
        tq = y.temiz_sorgu or ""
        if "Negated_Sector_Keyword:sağlık" not in tq and "negated" not in tq.lower():
            if "sağlık" in tq.lower() and "değil" not in tq.lower():
                reasons.append("Negated_Sector_Keyword:sağlık korunmadı")
        if y.sektor == "bilişim" and y.skor < 0.70:
            reasons.append(f"Bilişim conf {y.skor:.3f} < 0.70")
    return len(reasons) == 0, reasons


def run_layer(bot: Chatbot, layer: Layer) -> bool:
    print("\n" + "=" * 72)
    print(f"{layer.id} | {layer.baslik}")
    print("=" * 72)
    print(f"GIRDI : {layer.girdi}")

    y = bot.sor(layer.girdi)
    # Confidence: hem ham girdi hem temiz sorgu
    scores_raw = _confidence_table(bot, layer.girdi)
    scores_clean = _confidence_table(bot, y.temiz_sorgu or y.normalize_girdi)

    # Motor CPB notu (varsa)
    try:
        masked, aff, cpb = bot._contextual_probability_bias(
            bot._get_embedder(), y.normalize_girdi or layer.girdi
        )
    except Exception:
        masked, aff, cpb = set(), {}, ""

    print(f"CLEAN : {y.temiz_sorgu!r}")
    print(f"NORM  : {y.normalize_girdi!r}")
    print(f"SONUC : {y.sektor} / {y.mod} / {y.yontem} @ {y.skor:.3f}")
    print(f"ACIK  : {(y.aciklama or '')[:180]}")
    print("-" * 72)
    print(f"CONFIDENCE (ham girdi) : {_fmt_table(scores_raw)}")
    print(f"CONFIDENCE (temiz)     : {_fmt_table(scores_clean)}")
    if aff:
        print(
            f"MOTOR CPB aff          : "
            + ", ".join(f"{k}: {v:.2f}" for k, v in sorted(aff.items(), key=lambda x: -x[1]))
        )
        print(f"MOTOR CPB mask         : {sorted(masked) or '∅'} | {cpb}")
    print("-" * 72)

    ok, reasons = evaluate(y, layer)
    print(f"[{'PASS' if ok else 'FAIL'}] {layer.id}")
    for r in reasons:
        print(f"  !! {r}")
    return ok


def main() -> int:
    print("STRESS TEST CPB — 3 katman (motor koduna dokunulmadi)")
    bot = Chatbot(force_simulated_rewriter=True)
    print(f"Rewriter={bot._rewriter.mode} | Corpus={bot.corpus_boyutu()}")

    results: list[tuple[str, bool]] = []
    for layer in LAYERS:
        ok = run_layer(bot, layer)
        results.append((layer.id, ok))

    n_ok = sum(1 for _, ok in results if ok)
    n = len(results)
    print("\n" + "=" * 72)
    print(f"OZET: {n_ok}/{n} pass")
    for lid, ok in results:
        print(f"  {'✓' if ok else '✗'} {lid}")
    if n_ok == n:
        print("VERDICT: CPB matematiksel tutarli — ezber degil")
    else:
        print("VERDICT: KISMI / KIRILGAN — bazi katmanlar FAIL")
    print("=" * 72)
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
