"""K0 Allintos kaynak dogrulama."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import get_k0_data_source
from app.services.k0_corporate_info import invalidate_k0_records_cache, try_k0_corporate_info
from app.services.k0_knowledge_loader import load_allintos_k0_records


def main() -> None:
    os.environ["ALLINTOS_K0_SOURCE"] = "allintos"
    invalidate_k0_records_cache()

    remote = load_allintos_k0_records()
    print(f"[*] Allintos K0 virtual kayit: {len(remote)}")
    print(f"[*] Aktif kaynak: {get_k0_data_source()}")

    checks = [
        ("DDX nedir", "tr"),
        ("What is TRL", "en"),
        ("turquality", "tr"),
        ("e-turquality", "tr"),
        ("ddx", "en"),
    ]
    ok = 0
    for q, lang in checks:
        hit = try_k0_corporate_info(q, reply_lang=lang)
        good = hit is not None and bool(hit.get("cevap"))
        ok += int(good)
        mark = "OK" if good else "FAIL"
        src = hit.get("k0_source") if hit else "-"
        print(f"  [{mark}] {q!r} lang={lang} source={src} konu={hit.get('konu_etiketi') if hit else None}")

    print(f"\nSonuc: {ok}/{len(checks)}")
    if ok < len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
