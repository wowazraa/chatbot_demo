"""Intent Router JSON adaptörü — örnek çıktı.

    # Hızlı (BGE yok, sentetik yanıtlar):
    python scripts/demo_intent_router_json.py

    # Canlı motor ile:
    python scripts/demo_intent_router_json.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import ChatbotResponse


CASES = [
    "Kardiyoloji randevusu almak istiyorum",
    "HBYS kurulumu",
    "Antalya'da denize sıfır otel bakıyorum",
    "fiyat teklifi almak istiyorum",
    "bugün hava çok güzel",
]

# BGE olmadan spec şeklini göstermek için sabit örnekler
_SYNTH: list[ChatbotResponse] = [
    ChatbotResponse(
        girdi=CASES[0],
        normalize_girdi=CASES[0].lower(),
        sektor="sağlık",
        mod="K2",
        skor=0.91,
        yontem="bge-m3",
    ),
    ChatbotResponse(
        girdi=CASES[1],
        normalize_girdi="hbys kurulumu",
        sektor="sağlık",
        mod="K1",
        skor=1.0,
        yontem="kisaltma",
    ),
    ChatbotResponse(
        girdi=CASES[2],
        normalize_girdi=CASES[2].lower(),
        sektor="turizm",
        mod="K2",
        skor=0.87,
        yontem="bge-m3",
    ),
    ChatbotResponse(
        girdi=CASES[3],
        normalize_girdi=CASES[3].lower(),
        sektor="belirsiz",
        mod="FB",
        skor=0.58,
        yontem="fb",
    ),
    ChatbotResponse(
        girdi=CASES[4],
        normalize_girdi=CASES[4].lower(),
        sektor="belirsiz",
        mod="FB",
        skor=0.08,
        yontem="fb",
    ),
]


def _print_payload(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("---")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="Chatbot.sor() ile üret")
    args = ap.parse_args()

    if not args.live:
        latencies = [112, 18, 95, 70, 40]
        for r, ms in zip(_SYNTH, latencies):
            _print_payload(r.to_intent_router(latency_ms=ms))
        return

    from src.chatbot import Chatbot
    from src.embedder import reset_embedder

    reset_embedder()
    bot = Chatbot(force_simulated_rewriter=True)
    for q in CASES:
        t0 = time.perf_counter()
        r = bot.sor(q, session_id="router-demo")
        ms = (time.perf_counter() - t0) * 1000
        _print_payload(r.to_intent_router(latency_ms=ms))


if __name__ == "__main__":
    main()
