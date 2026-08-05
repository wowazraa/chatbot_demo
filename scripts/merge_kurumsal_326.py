"""
326 kurumsal kaydı raw + processed corpus'a ekler ve incremental index sync çalıştırır.

5659 augment kayıtlarına DOKUNMAZ — yalnızca append.

Kullanım:
    python scripts/prepare_kurumsal_326.py   # önce (data/external/kurumsal_326_prepared.json)
    python scripts/merge_kurumsal_326.py
    python scripts/merge_kurumsal_326.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.intent_mapping import source_id_for_record
from app.services.index_sync import SourceIdCollisionError, sync_new_qa_records

PREPARED = ROOT / "data" / "external" / "kurumsal_326_prepared.json"
RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
PROCESSED_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _backup(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = path.with_name(f"{path.stem}.pre_kurumsal_merge_{ts}{path.suffix}")
    shutil.copy2(path, dest)
    return dest


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Dosya/index yazmadan doğrula")
    args = parser.parse_args()

    if not PREPARED.exists():
        print(f"[!] Hazır kurumsal dosyası yok: {PREPARED}")
        print("    Önce: python scripts/prepare_kurumsal_326.py")
        sys.exit(1)

    prepared_doc = _load_json(PREPARED)
    new_records = list(prepared_doc.get("kayitlar") or [])
    if len(new_records) != 326:
        print(f"[!] Beklenen 326 kayıt, gelen {len(new_records)}")
        sys.exit(1)

    raw_doc = _load_json(RAW_PATH)
    proc_doc = _load_json(PROCESSED_PATH)
    raw_existing = list(raw_doc.get("kayitlar") or [])
    proc_existing = list(proc_doc.get("kayitlar") or [])

    existing_ids: set[str] = set()
    for i, r in enumerate(raw_existing):
        sid = r.get("source_id") or r.get("id")
        if sid is not None:
            existing_ids.add(str(sid))

    conflicts = [
        source_id_for_record(r)
        for r in new_records
        if str(source_id_for_record(r)) in existing_ids
    ]
    if conflicts:
        print(f"[!] source_id çakışması — merge durduruldu: {sorted(set(conflicts))[:10]}...")
        sys.exit(1)

    print(f"[+] Mevcut raw={len(raw_existing)}, processed={len(proc_existing)}")
    print(f"[+] Eklenecek kurumsal kayıt: {len(new_records)}")

    if args.dry_run:
        print("[dry-run] Yazma/index sync atlandı.")
        return

    raw_backup = _backup(RAW_PATH)
    proc_backup = _backup(PROCESSED_PATH)
    print(f"[+] Yedek: {raw_backup.name}, {proc_backup.name}")

    raw_merged = raw_existing + new_records
    proc_merged = proc_existing + new_records

    raw_doc["kayitlar"] = raw_merged
    raw_doc.setdefault("meta", {})["kurumsal_merge"] = {
        "tarih": datetime.now().isoformat(timespec="seconds"),
        "eklenen": len(new_records),
    }
    proc_doc["kayitlar"] = proc_merged
    proc_doc.setdefault("meta", {})["kurumsal_merge"] = raw_doc["meta"]["kurumsal_merge"]

    _write_json(RAW_PATH, raw_doc)
    _write_json(PROCESSED_PATH, proc_doc)
    print(f"[+] raw/processed yazıldı: raw={len(raw_merged)}, processed={len(proc_merged)}")

    try:
        sync_new_qa_records(new_records)
    except SourceIdCollisionError:
        raise
    except Exception as exc:
        print(f"[!] Index sync hatası: {exc}")
        sys.exit(1)

    print("[+] Merge + incremental index sync tamamlandı.")


if __name__ == "__main__":
    main()
