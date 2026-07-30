"""V2 pgvector şema sabitleri ve DDL.

Tablo: vector_index
  id, sector, sub_intent, text_content, embedding (bge-m3, 1024-d)
  + HNSW (cosine) indeksi — ANN Top-K için.
"""

from __future__ import annotations

EMBEDDING_DIM = 1024  # BAAI/bge-m3 dense
TABLE_NAME = "vector_index"
HNSW_INDEX_NAME = "idx_vector_index_embedding_hnsw"

# cosine distance ops — embedding <=> query ile uyumlu
DDL_STATEMENTS: tuple[str, ...] = (
    "CREATE EXTENSION IF NOT EXISTS vector;",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id              BIGSERIAL PRIMARY KEY,
        source_id       TEXT NOT NULL UNIQUE,
        sector          VARCHAR(32) NOT NULL,
        sub_intent      VARCHAR(64) NOT NULL,
        text_content    TEXT NOT NULL,
        embedding       vector({EMBEDDING_DIM}) NOT NULL,
        lang            VARCHAR(8) NOT NULL DEFAULT 'tr',
        meta            JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS {HNSW_INDEX_NAME}
        ON {TABLE_NAME}
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_sector
        ON {TABLE_NAME} (sector);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_sub_intent
        ON {TABLE_NAME} (sub_intent);
    """,
)
