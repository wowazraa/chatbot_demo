"""Pipeline smoke test — ALLINTOS_RETRIEVAL_MODE=primary ile."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("ALLINTOS_RETRIEVAL_MODE", "primary")

from app.services.pipeline_service import V2IntentPipeline

CASES = [
    ("hastane yonetim sistemi ariyoruz", "saglik", "SUCCESS"),
    ("otel rezervasyon yazilimi istiyoruz", "turizm", "SUCCESS"),
    ("okul yonetim sistemi arayisindayiz", "egitim", "SUCCESS"),
    ("kurumsal ERP entegrasyonu", "bilisim", "SUCCESS"),
    ("streaming platformu gelistirmek istiyoruz", "eglence", "SUCCESS"),
    ("TUBITAK nedir", "ood", "INFO"),
]


def main() -> None:
    pipe = V2IntentPipeline()
    ok = 0
    for query, exp_sector, exp_status in CASES:
        r = pipe.run(query)
        good = r.status == exp_status and (exp_status == "INFO" or r.sector == exp_sector)
        ok += int(good)
        mark = "OK" if good else "FAIL"
        print(f"[{mark}] {query!r} -> status={r.status} sector={r.sector} conf={r.confidence_score:.2f}")
    print(f"\nSonuc: {ok}/{len(CASES)}")
    if ok < len(CASES):
        sys.exit(1)


if __name__ == "__main__":
    main()
