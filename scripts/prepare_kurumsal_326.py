"""
326 kurumsal kaydı Desktop kaynağından merge-ready forma dönüştürür.

Çıktı: data/external/kurumsal_326_prepared.json (gitignore)

Kullanım:
    python scripts/prepare_kurumsal_326.py
    python scripts/prepare_kurumsal_326.py --source "C:/Users/.../chatbot_dataset(7).json"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.record_types import KAYIT_TIPI_KURUMSAL, transform_kurumsal_source_record

DEFAULT_SOURCE = Path.home() / "OneDrive" / "Desktop" / "chatbot_dataset(7).json"
OUT_PATH = ROOT / "data" / "external" / "kurumsal_326_prepared.json"
PROJ_RAW = ROOT / "data" / "raw" / "chatbot_dataset.json"


def norm_msg(rec: dict) -> str:
    return (rec.get("normalize_mesaj") or rec.get("mesaj") or "").strip().lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"[!] Kaynak bulunamadı: {args.source}")
        sys.exit(1)

    desktop = json.loads(args.source.read_text(encoding="utf-8"))
    proj_raw = json.loads(PROJ_RAW.read_text(encoding="utf-8"))
    proj_msgs = {norm_msg(r) for r in proj_raw.get("kayitlar", [])}

    kurumsal_src = [
        r for r in desktop.get("kayitlar", [])
        if r.get("beklenen_sektor") == "kurumsal"
    ]
    # Yalnızca projede olmayan mesajlar (326 beklenen)
    new_kurumsal = [r for r in kurumsal_src if norm_msg(r) not in proj_msgs]

    prepared = [transform_kurumsal_source_record(r) for r in new_kurumsal]

    # Doğrulama
    assert all(r.get("kayit_tipi") == KAYIT_TIPI_KURUMSAL for r in prepared)
    assert all("beklenen_sektor" not in r for r in prepared)
    assert all(r.get("cevap") for r in prepared)
    assert len(prepared) == 326, f"beklenen 326, gelen {len(prepared)}"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "kaynak": str(args.source),
            "kayit_sayisi": len(prepared),
            "kayit_tipi": KAYIT_TIPI_KURUMSAL,
            "not": "288 sektör/FB grubu bu turda dahil değil",
        },
        "kayitlar": prepared,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] {len(prepared)} kurumsal kayıt hazırlandı → {OUT_PATH}")


if __name__ == "__main__":
    main()
