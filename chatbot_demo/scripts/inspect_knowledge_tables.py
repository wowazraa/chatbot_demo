"""Canli Allintos DB — knowledge / kurumsal tablo kesfi."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.db.allintos_db import fetch_readonly

tables = fetch_readonly(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
)
print("=== knowledge / qa / intent tablolari ===")
for (t,) in tables:
    if any(k in t for k in ("knowledge", "qa_", "intent")):
        print(" ", t)

candidates = [
    "knowledge_documents",
    "knowledge_document_chunks",
    "knowledge_document_embeddings",
    "knowledge_documen",
]
seen = {t for (t,) in tables}
for tbl in candidates:
    if tbl not in seen:
        # prefix match
        matches = [t for (t,) in tables if t.startswith("knowledge")]
        if tbl == "knowledge_documen" and matches:
            for m in matches:
                if m not in candidates:
                    candidates.append(m)
        continue

for tbl in sorted({t for (t,) in tables if "knowledge" in t}):
    cols = fetch_readonly(
        """
        SELECT column_name, data_type, udt_name, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (tbl,),
    )
    print(f"\n=== {tbl} ({len(cols)} kolon) ===")
    for c in cols:
        print(f"  {c[0]:32} {c[1]:22} udt={c[2]:12} null={c[3]}")
    cnt = fetch_readonly(f"SELECT COUNT(*) FROM {tbl}")[0][0]
    print(f"  row_count: {cnt}")
    idx = fetch_readonly(
        """
        SELECT indexname, indexdef FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s
        """,
        (tbl,),
    )
    print("  indexes:")
    for name, idef in idx:
        print(f"    {name}: {idef[:100]}...")

    fk = fetch_readonly(
        """
        SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS ref_table, ccu.column_name AS ref_col
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'public' AND tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'
        """,
        (tbl,),
    )
    if fk:
        print("  foreign_keys:")
        for row in fk:
            print(f"    {row[1]} -> {row[2]}.{row[3]} ({row[0]})")

    if tbl == "knowledge_document_embeddings":
        dim = fetch_readonly(
            """
            SELECT a.atttypmod FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = 'embedding'
            """,
            (tbl,),
        )
        if dim:
            # atttypmod for vector is dimension + 4 header? pgvector uses typmod as dim
            print(f"  embedding_typmod: {dim[0][0]}")
