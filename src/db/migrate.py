"""vector_index tablosu + HNSW indeksi migration."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import get_engine
from src.db.schema import DDL_STATEMENTS, TABLE_NAME

_PGVECTOR_HINT = (
    "pgvector DB erişilemiyor.\n"
    "  1) Yerel Postgres (5432) ayakta olsun\n"
    "  2) chatbot_demo/.env -> "
    "postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_db\n"
    "  3) python -m db_api.setup_local_db\n"
    "  4) python scripts/seed_pgvector.py --truncate\n"
    "DB yokken runtime otomatik NPZ-dense fallback kullanır."
)


def ensure_schema(engine: Engine | None = None) -> None:
    """
    pgvector extension + vector_index + HNSW.
    Idempotent — birden fazla çağrı güvenli.
    """
    eng = engine or get_engine()
    try:
        with eng.begin() as conn:
            for stmt in DDL_STATEMENTS:
                conn.execute(text(stmt))
    except SQLAlchemyError as exc:
        msg = str(exc).lower()
        if "vector" in msg or "extension" in msg:
            raise RuntimeError(_PGVECTOR_HINT) from exc
        raise


def table_exists(engine: Engine | None = None) -> bool:
    eng = engine or get_engine()
    with eng.connect() as conn:
        row = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'public' AND table_name = :t"
                ")"
            ),
            {"t": TABLE_NAME},
        ).scalar()
    return bool(row)


def row_count(engine: Engine | None = None) -> int:
    eng = engine or get_engine()
    with eng.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()
    return int(n or 0)
