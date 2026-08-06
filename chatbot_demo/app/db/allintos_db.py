"""Allintos (Sinem) PostgreSQL — intent_code lookup ve salt-okunur bağlantı."""

from __future__ import annotations

import os
import threading
from typing import Final
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import connection as PgConnection

from app.core.config import load_dotenv
from app.core.intent_mapping import SEKTOR_TO_INTENT, resolve_intent

load_dotenv()

# 5 hizmet sektörü — kurumsal / OOD hariç
SERVICE_SECTORS: Final[tuple[str, ...]] = (
    "turizm",
    "saglik",
    "egitim",
    "bilisim",
    "eglence",
)

CANONICAL_SERVICE_INTENT_CODES: Final[tuple[str, ...]] = tuple(
    SEKTOR_TO_INTENT[s] for s in SERVICE_SECTORS
)

_INTENT_ID_CACHE: dict[str, int] = {}
_cache_lock = threading.Lock()


def get_allintos_write_url() -> str | None:
    url = (os.getenv("ALLINTOS_DB_URL") or "").strip()
    return url or None


def get_allintos_readonly_url() -> str | None:
    url = (os.getenv("ALLINTOS_READONLY_DB_URL") or "").strip()
    return url or None


def _psycopg2_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg2://", "postgresql://")


def _apply_readonly_session(conn: PgConnection) -> None:
    """Salt-okunur oturum — yalnızca SELECT (yazma yollarından ayrı)."""
    conn.set_session(readonly=True, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
        cur.execute("SET default_transaction_read_only = on")
    finally:
        cur.close()


def connect_allintos_write() -> PgConnection:
    """Yazma/sync yolu — _sync_allintos vb. (readonly DEĞİL)."""
    url = get_allintos_write_url()
    if not url:
        raise RuntimeError("ALLINTOS_DB_URL tanımlı değil.")
    return psycopg2.connect(_psycopg2_dsn(url))


def connect_allintos(*, readonly: bool = False) -> PgConnection:
    if readonly:
        url = get_allintos_readonly_url()
        if not url:
            raise RuntimeError("ALLINTOS_READONLY_DB_URL tanımlı değil.")
        conn = psycopg2.connect(_psycopg2_dsn(url))
        _apply_readonly_session(conn)
        return conn
    return connect_allintos_write()


def fetch_readonly(sql: str, params: tuple | dict | None = None) -> list[tuple]:
    """Shadow / keşif — yalnız SELECT, readonly bağlantı."""
    normalized = " ".join(sql.strip().split()).upper()
    if not normalized.startswith("SELECT"):
        raise RuntimeError("Readonly path: yalnizca SELECT izinli.")
    conn = connect_allintos(readonly=True)
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.rollback()
        return rows
    finally:
        cur.close()
        conn.close()


def is_allintos_readonly_configured() -> bool:
    return bool(get_allintos_readonly_url())


def refresh_intent_id_cache(*, db_url: str | None = None, conn: PgConnection | None = None) -> dict[str, int]:
    """intent_code → id haritasını DB'den yükler (sabit sayı yok)."""
    own_conn = conn is None
    if own_conn:
        url = db_url or get_allintos_write_url()
        if not url:
            raise RuntimeError("Allintos DB URL yok — intent cache yüklenemedi.")
        conn = connect_allintos_write() if db_url is None else psycopg2.connect(_psycopg2_dsn(url))

    assert conn is not None
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, intent_code
            FROM intents
            WHERE intent_code = ANY(%s)
            ORDER BY intent_code
            """,
            (list(CANONICAL_SERVICE_INTENT_CODES),),
        )
        mapping = {str(code): int(row_id) for row_id, code in cur.fetchall()}
    finally:
        cur.close()
        if own_conn:
            conn.close()

    with _cache_lock:
        _INTENT_ID_CACHE.clear()
        _INTENT_ID_CACHE.update(mapping)
    return dict(mapping)


def _intent_code_for_sector(sector: str) -> str | None:
    code = resolve_intent(sector)
    if code in ("ood", "corporate_info"):
        return None
    if code not in CANONICAL_SERVICE_INTENT_CODES:
        return None
    return code


def resolve_intent_id_for_sector(sector: str, *, db_url: str | None = None) -> int | None:
    """
    Sektör slug → intents.id (intent_code üzerinden, hardcode ID yok).
    db_url verilmezse ALLINTOS_DB_URL kullanılır (yazma sync yolu).
    """
    intent_code = _intent_code_for_sector(sector)
    if not intent_code:
        return None

    with _cache_lock:
        cached = _INTENT_ID_CACHE.get(intent_code)

    if cached is not None:
        return cached

    url = db_url or get_allintos_write_url()
    if not url:
        return None

    refresh_intent_id_cache(db_url=url)
    with _cache_lock:
        return _INTENT_ID_CACHE.get(intent_code)


def invalidate_intent_id_cache() -> None:
    with _cache_lock:
        _INTENT_ID_CACHE.clear()


def mask_db_url(url: str) -> str:
    """Log için parola maskele."""
    parsed = urlparse(_psycopg2_dsn(url))
    host = parsed.hostname or "?"
    port = parsed.port or 5432
    user = parsed.username or "?"
    db = (parsed.path or "/").lstrip("/") or "?"
    return f"postgresql://{user}:***@{host}:{port}/{db}"
