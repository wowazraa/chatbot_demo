"""Allintos DB yazma fonksiyonunu izole test eder.

Admin panel / add_qa endpoint / lokal JSON dosyalarına DOKUNMAZ.
Sadece index_sync._sync_allintos çağrılır.

Kullanım:
  1. .env içinde ALLINTOS_DB_ENABLED=true yap
  2. python scripts/test_allintos_db_isolated.py write
  3. pgAdmin'de SELECT ile doğrula (komut aşağıda)
  4. python scripts/test_allintos_db_isolated.py cleanup
  5. .env içinde ALLINTOS_DB_ENABLED=false yap
  6. python scripts/test_allintos_db_isolated.py check-local

pgAdmin doğrulama:
  SELECT * FROM qa_embeddings WHERE question LIKE '%AZRA-MINIMAL-KONTROL%';

Temizlik (script yerine elle de yapılabilir):
  DELETE FROM qa_embeddings WHERE question LIKE '%AZRA-MINIMAL-KONTROL%';
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

TEST_QUESTION = "AZRA-MINIMAL-KONTROL"
TEST_RECORD = [
    {
        "mesaj": TEST_QUESTION,
        "cevap": "test",
        "beklenen_sektor": "turizm",
        "is_augmented": False,
    }
]

LOCAL_DATASETS = (
    "data/raw/chatbot_dataset.json",
    "data/processed/chatbot_dataset_augmented.json",
)


def _db_url() -> str:
    url = os.getenv("ALLINTOS_DB_URL", "")
    return url.replace("postgresql+psycopg2://", "postgresql://")


def cmd_write() -> None:
    from app.services.index_sync import _sync_allintos, encode_new_records

    print("ALLINTOS_DB_ENABLED =", os.getenv("ALLINTOS_DB_ENABLED"))
    print("ALLINTOS_DB_URL =", os.getenv("ALLINTOS_DB_URL"))
    print("--- _sync_allintos (isolated) ---")
    _, _, dense, _ = encode_new_records(TEST_RECORD)
    _sync_allintos(TEST_RECORD, dense)
    print("--- yazma tamam ---")
    print(f"pgAdmin: SELECT * FROM qa_embeddings WHERE question LIKE '%{TEST_QUESTION}%';")


def cmd_verify() -> None:
    conn = psycopg2.connect(_db_url())
    cur = conn.cursor()
    cur.execute(
        "SELECT id, intent_id, question, answer, is_augmented, created_at "
        "FROM qa_embeddings WHERE question LIKE %s",
        (f"%{TEST_QUESTION}%",),
    )
    rows = cur.fetchall()
    print(f"Kayit sayisi: {len(rows)}")
    for row in rows:
        print(row)
    cur.close()
    conn.close()


def cmd_cleanup() -> None:
    conn = psycopg2.connect(_db_url())
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM qa_embeddings WHERE question LIKE %s",
        (f"%{TEST_QUESTION}%",),
    )
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Silinen kayit: {deleted}")
    cmd_verify()


def cmd_check_local() -> None:
    for rel in LOCAL_DATASETS:
        p = ROOT / rel
        if not p.exists():
            print(f"{rel}: dosya yok")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        n = len(d.get("kayitlar", []))
        print(f"{rel}: len(kayitlar)={n}")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    actions = {
        "write": cmd_write,
        "verify": cmd_verify,
        "cleanup": cmd_cleanup,
        "check-local": cmd_check_local,
    }
    if cmd not in actions:
        print(f"Bilinmeyen komut: {cmd}")
        print("Gecerli: write | verify | cleanup | check-local")
        sys.exit(1)

    actions[cmd]()


if __name__ == "__main__":
    main()
