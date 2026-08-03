"""PostgreSQL bağlantısı — V2 vector_index için (V1 / db_api'den bağımsız)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_ROOT = Path(__file__).resolve().parents[2]  # chatbot_demo/


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # chatbot_demo/.env öncelikli
    env_path = _ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
    else:
        load_dotenv(override=False)


def get_connection_url() -> str:
    """DATABASE_URL veya yerel Postgres varsayılanı (5432 / chatbot_db)."""
    _load_dotenv()
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        return url
    return (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_db"
    )


@lru_cache(maxsize=1)
def get_engine(*, echo: bool = False) -> Engine:
    """Lazy singleton SQLAlchemy engine."""
    return create_engine(
        get_connection_url(),
        pool_pre_ping=True,
        future=True,
        echo=echo,
    )


def reset_engine() -> None:
    """Testler için engine cache temizliği."""
    get_engine.cache_clear()
