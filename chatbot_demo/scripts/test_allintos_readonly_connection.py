"""Allintos readonly baglanti + SELECT-only zorlamasi testi.

  python scripts/test_allintos_readonly_connection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import load_dotenv as _ld

_ld()

from app.db.allintos_db import (
    connect_allintos,
    connect_allintos_write,
    fetch_readonly,
    get_allintos_readonly_url,
    mask_db_url,
    refresh_intent_id_cache,
    resolve_intent_id_for_sector,
)


def test_select_counts() -> None:
    url = get_allintos_readonly_url()
    print("readonly_url:", mask_db_url(url or ""))
    assert fetch_readonly("SELECT 1")[0][0] == 1
    qa_count = fetch_readonly("SELECT COUNT(*) FROM qa_embeddings")[0][0]
    intent_count = fetch_readonly("SELECT COUNT(*) FROM intents")[0][0]
    print(f"[OK] SELECT 1, qa_embeddings={qa_count}, intents={intent_count}")


def test_intent_code_lookup_live() -> None:
    rows = fetch_readonly(
        "SELECT id, intent_code FROM intents WHERE intent_code = %s",
        ("bilisim_integration",),
    )
    assert rows, "bilisim_integration intents tablosunda yok"
    db_id = int(rows[0][0])
    cached_id = resolve_intent_id_for_sector("bilisim")
    print(f"[OK] bilisim_integration id={db_id}, resolve_intent_id_for_sector(bilisim)={cached_id}")
    assert cached_id == db_id


def test_readonly_rejects_insert() -> None:
    conn = connect_allintos(readonly=True)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO qa_embeddings (question, answer, intent_id, embedding, is_augmented) "
            "VALUES ('shadow_test', 'x', 1, "
            "'[" + ",".join(["0"] * 1024) + "]', false)"
        )
        conn.commit()
        raise AssertionError("INSERT readonly oturumda basarili oldu — beklenmiyordu")
    except psycopg2.Error as exc:
        conn.rollback()
        print(f"[OK] INSERT reddedildi: {type(exc).__name__}: {exc.pgerror or exc}")
    finally:
        cur.close()
        conn.close()


def test_readonly_rejects_update() -> None:
    conn = connect_allintos(readonly=True)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE intents SET url = url WHERE id = 1")
        conn.commit()
        raise AssertionError("UPDATE readonly oturumda basarili oldu — beklenmiyordu")
    except psycopg2.Error as exc:
        conn.rollback()
        print(f"[OK] UPDATE reddedildi: {type(exc).__name__}: {exc.pgerror or exc}")
    finally:
        cur.close()
        conn.close()


def test_fetch_readonly_rejects_non_select() -> None:
    try:
        fetch_readonly("DELETE FROM qa_embeddings WHERE id = 1")
        raise AssertionError("fetch_readonly DELETE kabul etti")
    except RuntimeError as exc:
        print(f"[OK] fetch_readonly non-SELECT reddi: {exc}")


def main() -> None:
    if not get_allintos_readonly_url():
        print("ALLINTOS_READONLY_DB_URL tanimli degil")
        sys.exit(1)
    test_select_counts()
    test_intent_code_lookup_live()
    test_readonly_rejects_insert()
    test_readonly_rejects_update()
    test_fetch_readonly_rejects_non_select()
    print("--- tum readonly testleri gecti ---")


if __name__ == "__main__":
    main()
