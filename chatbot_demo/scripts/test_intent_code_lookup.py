"""intent_code → id lookup testleri (DB mock + opsiyonel canlı Allintos).

  python scripts/test_intent_code_lookup.py
  python scripts/test_intent_code_lookup.py --live   # ALLINTOS_DB_URL gerekir
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.intent_mapping import SEKTOR_TO_INTENT, resolve_intent
from app.db import allintos_db


def test_sector_to_intent_code() -> None:
    assert resolve_intent("bilisim") == "bilisim_integration"
    assert resolve_intent("turizm") == "tourism_hotel"
    assert SEKTOR_TO_INTENT["saglik"] == "health_appointment"
    print("[OK] sektor -> intent_code sabit eslesme")


def test_intent_id_lookup_with_mock_db() -> None:
    allintos_db.invalidate_intent_id_cache()

    mock_rows = [
        (1, "tourism_hotel"),
        (2, "health_appointment"),
        (3, "education_enrollment"),
        (4, "bilisim_integration"),
        (5, "eglence_streaming"),
    ]
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = mock_rows
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch.object(allintos_db, "get_allintos_write_url", return_value="postgresql://u:p@h/db"):
        with patch.object(allintos_db.psycopg2, "connect", return_value=mock_conn):
            intent_id = allintos_db.resolve_intent_id_for_sector("bilisim")

    assert intent_id == 4, f"beklenen 4 (bilisim_integration), gelen {intent_id}"
    assert allintos_db._INTENT_ID_CACHE.get("bilisim_integration") == 4
    print("[OK] mock DB intent_code lookup (bilisim -> id=4)")


def test_kurumsal_sector_returns_none() -> None:
    allintos_db.invalidate_intent_id_cache()
    assert allintos_db.resolve_intent_id_for_sector("kurumsal") is None
    print("[OK] kurumsal sektor -> None (sync disi)")


def test_live_lookup() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    allintos_db.invalidate_intent_id_cache()
    mapping = allintos_db.refresh_intent_id_cache()
    print("[LIVE] intent cache:", mapping)
    for sector in allintos_db.SERVICE_SECTORS:
        code = resolve_intent(sector)
        iid = allintos_db.resolve_intent_id_for_sector(sector)
        print(f"  {sector} -> {code} -> id={iid}")
        assert iid is not None, f"canli DB'de {sector} icin id yok"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="ALLINTOS_DB_URL ile canli DB testi")
    args = parser.parse_args()

    test_sector_to_intent_code()
    test_intent_id_lookup_with_mock_db()
    test_kurumsal_sector_returns_none()
    if args.live:
        test_live_lookup()
    else:
        print("[SKIP] canli DB (--live ile calistir)")
    print("--- tum testler gecti ---")


if __name__ == "__main__":
    main()
