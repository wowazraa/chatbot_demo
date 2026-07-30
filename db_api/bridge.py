"""DB köprüsü — chatbot_demo/.env öncelikli; pgvector yoksa yerel modeller."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_CHATBOT_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _CHATBOT_ROOT.parent
_DB_PKG = (
    _PROJECT_ROOT
    / "veritabani_kurgusu_test_seneryolari"
    / "veritabani_kurgusu_test_seneryolari"
)

try:
    from dotenv import load_dotenv

    # Sibling .env varsa önce onu, chatbot_demo/.env her zaman kazanır
    if (_DB_PKG / ".env").exists():
        load_dotenv(_DB_PKG / ".env")
    load_dotenv(_CHATBOT_ROOT / ".env", override=True)
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL yok. chatbot_demo/.env oluşturun veya "
        "python -m db_api.setup_local_db çalıştırın."
    )

# Windows psycopg2 DLL yolu
if sys.platform == "win32":
    pg_base = r"C:\Program Files\PostgreSQL"
    if os.path.exists(pg_base):
        for version in os.listdir(pg_base):
            pg_bin = os.path.join(pg_base, version, "bin")
            if os.path.isdir(pg_bin):
                try:
                    os.add_dll_directory(pg_bin)
                except Exception:
                    pass

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _detect_pgvector() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).first()
            if row:
                return True
            # kolon tipi vector mi?
            col = conn.execute(
                text(
                    """
                    SELECT data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_name = 'qa_embeddings' AND column_name = 'embedding'
                    """
                )
            ).first()
            if col and (col[1] == "vector" or col[0] == "USER-DEFINED"):
                return True
    except Exception:
        return False
    return False


USE_PGVECTOR = _detect_pgvector()

if USE_PGVECTOR and _DB_PKG.is_dir():
    if str(_DB_PKG) not in sys.path:
        sys.path.insert(0, str(_DB_PKG))
    from models import (  # type: ignore  # noqa: E402
        EMBEDDING_DIM,
        AdminUser,
        AnalyticsEvent,
        Blog,
        Company,
        Conversation,
        Intent,
        Message,
        QaEmbedding,
        Sector,
        Session as ChatSession,
    )
else:
    from db_api.models_local import (  # noqa: E402
        EMBEDDING_DIM,
        AdminUser,
        AnalyticsEvent,
        Blog,
        Company,
        Conversation,
        Intent,
        Message,
        QaEmbedding,
        Sector,
        Session as ChatSession,
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "EMBEDDING_DIM",
    "USE_PGVECTOR",
    "AdminUser",
    "AnalyticsEvent",
    "Blog",
    "ChatSession",
    "Company",
    "Conversation",
    "Intent",
    "Message",
    "QaEmbedding",
    "Sector",
    "SessionLocal",
    "engine",
    "get_db",
]
