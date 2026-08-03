"""Geriye dönük uyumluluk — app.services.session_service kullanın."""

from app.services.session_service import persist_chat_turn  # noqa: F401

__all__ = ["persist_chat_turn"]
