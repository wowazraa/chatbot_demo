"""Geriye dönük uyumluluk — uvicorn db_api.main:app yerine main:app tercih edin."""

from main import app  # noqa: F401

__all__ = ["app"]
