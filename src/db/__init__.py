"""V2 pgvector altyapısı — V1 NPZ yolundan bağımsız."""

from __future__ import annotations

from src.db.connection import get_connection_url, get_engine, reset_engine
from src.db.migrate import ensure_schema, row_count, table_exists
from src.db.npz_store import NpzDenseStore
from src.db.schema import EMBEDDING_DIM, TABLE_NAME
from src.db.store_factory import open_vector_store, probe_pgvector
from src.db.vector_store import VectorCandidate, VectorIndexStore

__all__ = [
    "EMBEDDING_DIM",
    "TABLE_NAME",
    "NpzDenseStore",
    "VectorCandidate",
    "VectorIndexStore",
    "ensure_schema",
    "get_connection_url",
    "get_engine",
    "open_vector_store",
    "probe_pgvector",
    "reset_engine",
    "row_count",
    "table_exists",
]
