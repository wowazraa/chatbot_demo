"""Yerel Postgres kurulumu.

- chatbot_db oluşturur
- pgvector varsa VECTOR(1024) şemasını uygular (sibling schema.sql)
- yoksa float[] ile uyumlu yedek DDL uygular (Postman testleri için)

Kullanım:
  python -m db_api.setup_local_db
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

ADMIN_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)
DB_NAME = os.getenv("POSTGRES_DB", "chatbot_db")
TARGET_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://postgres:postgres@localhost:5432/{DB_NAME}",
).replace("postgresql+psycopg2://", "postgresql://")


FALLBACK_DDL = r"""
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS sectors (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sector_key     VARCHAR(50) NOT NULL UNIQUE,
    sector_name_tr VARCHAR(100) NOT NULL,
    sector_name_en VARCHAR(100) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS intents (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    intent_code   VARCHAR(100) NOT NULL UNIQUE,
    url           VARCHAR(500) NOT NULL,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_intents_intent_code_not_blank CHECK (BTRIM(intent_code) <> ''),
    CONSTRAINT ck_intents_url_not_blank CHECK (BTRIM(url) <> '')
);

CREATE TABLE IF NOT EXISTS admin_users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'editor',
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_admin_users_role CHECK (role IN ('admin', 'editor'))
);

CREATE TABLE IF NOT EXISTS blogs (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug         VARCHAR(255) NOT NULL UNIQUE,
    title_tr     VARCHAR(255) NOT NULL,
    title_en     VARCHAR(255) NOT NULL,
    content_tr   TEXT NOT NULL,
    content_en   TEXT NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT false,
    published_at TIMESTAMPTZ,
    author_id    INTEGER REFERENCES admin_users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_blogs_publish_consistency CHECK (
        (is_published = false) OR (is_published = true AND published_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS companies (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL UNIQUE,
    sector_id    INTEGER REFERENCES sectors(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_name    VARCHAR(255) NOT NULL,
    user_identifier VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_sessions_status CHECK (status IN ('active', 'closed', 'expired')),
    CONSTRAINT ck_sessions_closed_at_consistency CHECK (
        (status = 'active' AND closed_at IS NULL)
        OR (status IN ('closed', 'expired') AND closed_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    role            VARCHAR(10) NOT NULL,
    intent          VARCHAR(100),
    source          VARCHAR(100) DEFAULT 'web',
    confidence      DOUBLE PRECISION,
    response_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_messages_role CHECK (role IN ('user', 'bot'))
);

CREATE TABLE IF NOT EXISTS qa_embeddings (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    intent_id    INTEGER NOT NULL REFERENCES intents(id) ON DELETE RESTRICT,
    is_augmented BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding    DOUBLE PRECISION[] NOT NULL,
    CONSTRAINT ck_qa_embeddings_question_not_blank CHECK (BTRIM(question) <> ''),
    CONSTRAINT ck_qa_embeddings_answer_not_blank CHECK (BTRIM(answer) <> '')
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    intent      VARCHAR(100),
    layer_hit   VARCHAR(100),
    response_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_companies_sector_id ON companies(sector_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_identifier ON sessions(user_identifier);
CREATE INDEX IF NOT EXISTS idx_blogs_is_published ON blogs(is_published);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_qa_embeddings_intent_id ON qa_embeddings(intent_id);

CREATE OR REPLACE VIEW session_transcripts AS
SELECT
    c.session_id,
    string_agg(m.role || ': ' || m.content, E'\n' ORDER BY m.created_at, m.id) AS transcript
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
GROUP BY c.session_id;
"""


def _connect(url: str):
    return psycopg2.connect(url)


def ensure_database() -> None:
    conn = _connect(ADMIN_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone() is None:
        # template0 + UTF8 — Türkçe karakter (ğ, ı, ş) için zorunlu
        cur.execute(
            f'CREATE DATABASE "{DB_NAME}" '
            f"WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE template0"
        )
        print(f"[+] Database created (UTF8): {DB_NAME}")
    else:
        cur.execute("SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = %s", (DB_NAME,))
        enc = cur.fetchone()[0]
        print(f"[=] Database exists: {DB_NAME} (encoding={enc})")
        if enc.upper() not in ("UTF8", "UTF-8"):
            print(
                f"[!] UYARI: encoding={enc}. Türkçe karakterler 500 verebilir. "
                f"DROP DATABASE {DB_NAME}; sonra setup'ı tekrar çalıştırın."
            )
    cur.close()
    conn.close()


def has_vector(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ok = cur.fetchone() is not None
    cur.close()
    return ok


def apply_schema() -> str:
    conn = _connect(TARGET_URL)
    conn.autocommit = True
    cur = conn.cursor()
    mode = "fallback-float-array"
    if has_vector(conn):
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        sibling = (
            _ROOT.parent
            / "veritabani_kurgusu_test_seneryolari"
            / "veritabani_kurgusu_test_seneryolari"
            / "schema.sql"
        )
        if sibling.exists():
            cur.execute(sibling.read_text(encoding="utf-8"))
            mode = "pgvector-schema.sql"
            print(f"[+] Applied sibling schema.sql with pgvector")
        else:
            cur.execute(FALLBACK_DDL)
            print("[+] Applied fallback DDL (schema.sql missing)")
    else:
        cur.execute(FALLBACK_DDL)
        print("[+] pgvector yok — fallback DDL (embedding = double precision[])")
        print("    Not: QA search endpoint'i cosine için pgvector ister; diğer CRUD'lar çalışır.")
    cur.close()
    conn.close()
    return mode


def main() -> None:
    print(f"Admin : {ADMIN_URL}")
    print(f"Target: {TARGET_URL}")
    ensure_database()
    mode = apply_schema()
    print(f"[done] mode={mode}")
    print("Sonra: uvicorn db_api.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
