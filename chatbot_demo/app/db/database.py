"""PostgreSQL bağlantısı — ORM ve oturum fabrikası."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import DB_PKG, configure_windows_pg_dll, get_database_url, load_dotenv

load_dotenv()
configure_windows_pg_dll()

DATABASE_URL = get_database_url()

engine = create_engine(DATABASE_URL, echo=False, future=True)

from sqlalchemy import event
@event.listens_for(engine, "connect")
def register_pgvector(dbapi_connection, connection_record):
    try:
        from pgvector.psycopg2 import register_vector
        register_vector(dbapi_connection)
    except Exception:
        pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Sinem's Project DB Session Factory
from app.db.allintos_db import get_allintos_write_url
allintos_url = get_allintos_write_url()
if allintos_url:
    allintos_engine = create_engine(allintos_url, echo=False, future=True)
    @event.listens_for(allintos_engine, "connect")
    def register_pgvector_allintos(dbapi_connection, connection_record):
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(dbapi_connection)
        except Exception:
            pass
    AllintosSessionLocal = sessionmaker(bind=allintos_engine, autoflush=False, autocommit=False, future=True)
else:
    AllintosSessionLocal = SessionLocal

def get_allintos_db():
    db = AllintosSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _detect_pgvector() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).first()
            if row:
                return True
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

if USE_PGVECTOR and DB_PKG.is_dir():
    if str(DB_PKG) not in sys.path:
        sys.path.insert(0, str(DB_PKG))
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
    from app.models.tables import (  # noqa: E402
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


def get_chat_db():
    """Oturum/sohbet — Allintos veya yerel DB (ALLINTOS_CHAT_DB)."""
    from app.core.config import use_allintos_chat_db

    if use_allintos_chat_db() and allintos_url:
        db = AllintosSessionLocal()
    else:
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
    "get_allintos_db",
    "get_chat_db",
]
