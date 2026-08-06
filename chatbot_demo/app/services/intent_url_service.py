"""Intent redirect URL — Allintos intents tablosu (cache)."""

from __future__ import annotations

import threading

from app.core.intent_mapping import SEKTOR_TO_INTENT

_cache_lock = threading.Lock()
_url_cache: dict[str, str] = {}


def _sector_to_intent_code(sector: str) -> str | None:
    code = SEKTOR_TO_INTENT.get((sector or "").strip().lower())
    if not code or code == "ood":
        return None
    return code


def refresh_intent_url_cache() -> dict[str, str]:
    from app.core.config import use_allintos_chat_db
    from app.db.allintos_db import fetch_readonly

    if use_allintos_chat_db():
        rows = fetch_readonly("SELECT intent_code, url FROM intents ORDER BY intent_code")
    else:
        from app.db.database import SessionLocal, Intent

        db = SessionLocal()
        try:
            rows = [(r.intent_code, r.url) for r in db.query(Intent).order_by(Intent.intent_code).all()]
        finally:
            db.close()

    mapping = {str(code): str(url) for code, url in rows if code and url}
    with _cache_lock:
        _url_cache.clear()
        _url_cache.update(mapping)
    return dict(mapping)


def resolve_intent_url(sector: str, status: str) -> str | None:
    """SUCCESS sektor yonlendirme URL'si — Allintos intents."""
    if status != "SUCCESS" or (sector or "").strip().lower() in ("", "ood"):
        return None

    intent_code = _sector_to_intent_code(sector)
    if not intent_code:
        return None

    with _cache_lock:
        cached = _url_cache.get(intent_code)

    if cached is not None:
        return cached or None

    refresh_intent_url_cache()
    with _cache_lock:
        return _url_cache.get(intent_code)
