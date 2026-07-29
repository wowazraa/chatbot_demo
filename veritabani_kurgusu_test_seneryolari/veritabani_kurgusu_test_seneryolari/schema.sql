-- Chatbot / Bilgi Merkezi Projesi — PostgreSQL Şema (Sadeleştirilmiş - v6)
-- PostgreSQL 16 + pgvector üzerinde tasarlandı.
-- Kaynak: models.py ile birebir aynı kısıt, tip ve ilişkilere sahiptir (Toplam 11 Tablo).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Sektörler (iki dilli)
CREATE TABLE sectors (
    id             INTEGER GENERATED ALWAYS AS IDENTITY,
    sector_key     VARCHAR(50) NOT NULL,
    sector_name_tr VARCHAR(100) NOT NULL,
    sector_name_en VARCHAR(100) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_sectors PRIMARY KEY (id),
    CONSTRAINT uq_sectors_sector_key UNIQUE (sector_key)
);

-- Konuşma niyeti kataloğu (sektörden bağımsız)
CREATE TABLE intents (
    id            INTEGER GENERATED ALWAYS AS IDENTITY,
    intent_code   VARCHAR(100) NOT NULL,
    url           VARCHAR(500) NOT NULL,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_intents PRIMARY KEY (id),
    CONSTRAINT uq_intents_intent_code UNIQUE (intent_code),
    CONSTRAINT ck_intents_intent_code_not_blank CHECK (BTRIM(intent_code) <> ''),
    CONSTRAINT ck_intents_url_not_blank CHECK (BTRIM(url) <> '')
);
CREATE TRIGGER trg_intents_updated_at BEFORE UPDATE ON intents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Admin kullanıcıları
CREATE TABLE admin_users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY,
    username      VARCHAR(100) NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'editor',
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_admin_users PRIMARY KEY (id),
    CONSTRAINT uq_admin_users_username UNIQUE (username),
    CONSTRAINT uq_admin_users_email UNIQUE (email),
    CONSTRAINT ck_admin_users_role CHECK (role IN ('admin', 'editor'))
);
CREATE TRIGGER trg_admin_users_updated_at BEFORE UPDATE ON admin_users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Blog içerikleri (iki dilli, dashboard üzerinden yönetilir)
CREATE TABLE blogs (
    id           INTEGER GENERATED ALWAYS AS IDENTITY,
    slug         VARCHAR(255) NOT NULL,
    title_tr     VARCHAR(255) NOT NULL,
    title_en     VARCHAR(255) NOT NULL,
    content_tr   TEXT NOT NULL,
    content_en   TEXT NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT false,
    published_at TIMESTAMPTZ,
    author_id    INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_blogs PRIMARY KEY (id),
    CONSTRAINT uq_blogs_slug UNIQUE (slug),
    CONSTRAINT fk_blogs_author_id_admin_users FOREIGN KEY (author_id) REFERENCES admin_users(id) ON DELETE SET NULL,
    CONSTRAINT ck_blogs_publish_consistency CHECK (
        (is_published = false) OR (is_published = true AND published_at IS NOT NULL)
    )
);
CREATE TRIGGER trg_blogs_updated_at BEFORE UPDATE ON blogs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Şirketler
CREATE TABLE companies (
    id           INTEGER GENERATED ALWAYS AS IDENTITY,
    company_name VARCHAR(255) NOT NULL,
    sector_id    INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_companies PRIMARY KEY (id),
    CONSTRAINT uq_companies_company_name UNIQUE (company_name),
    CONSTRAINT fk_companies_sector_id_sectors FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE SET NULL
);
CREATE TRIGGER trg_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Oturumlar
CREATE TABLE sessions (
    id              INTEGER GENERATED ALWAYS AS IDENTITY,
    session_name    VARCHAR(255) NOT NULL,
    user_identifier VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_sessions PRIMARY KEY (id),
    CONSTRAINT ck_sessions_status CHECK (status IN ('active', 'closed', 'expired')),
    CONSTRAINT ck_sessions_closed_at_consistency CHECK (
        (status = 'active' AND closed_at IS NULL)
        OR (status IN ('closed', 'expired') AND closed_at IS NOT NULL)
    )
);
CREATE TRIGGER trg_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Konuşmalar (Oturum içindeki konuşma başlıkları)
CREATE TABLE conversations (
    id         INTEGER GENERATED ALWAYS AS IDENTITY,
    session_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_conversations PRIMARY KEY (id),
    CONSTRAINT fk_conversations_session_id_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Konuşmadaki bireysel mesajlar (Kullanıcı-Bot Mesajları)
CREATE TABLE messages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY,
    conversation_id INTEGER NOT NULL,
    content         TEXT NOT NULL,
    role            VARCHAR(10) NOT NULL,
    intent          VARCHAR(100),
    source          VARCHAR(100) DEFAULT 'web',
    confidence      DOUBLE PRECISION,
    response_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_messages PRIMARY KEY (id),
    CONSTRAINT fk_messages_conversation_id_conversations FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT ck_messages_role CHECK (role IN ('user', 'bot'))
);

-- Soru-Cevap bilgi bankası (Vektör Bilgi Bankası)
CREATE TABLE qa_embeddings (
    id              INTEGER GENERATED ALWAYS AS IDENTITY,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    intent_id       INTEGER NOT NULL,
    is_augmented    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding       VECTOR(1024) NOT NULL,
    CONSTRAINT pk_qa_embeddings PRIMARY KEY (id),
    CONSTRAINT fk_qa_embeddings_intent_id_intents FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE RESTRICT,
    CONSTRAINT ck_qa_embeddings_question_not_blank CHECK (BTRIM(question) <> ''),
    CONSTRAINT ck_qa_embeddings_answer_not_blank CHECK (BTRIM(answer) <> '')
);

-- Analitik olaylar
CREATE TABLE analytics_events (
    id          INTEGER GENERATED ALWAYS AS IDENTITY,
    session_id  INTEGER NOT NULL,
    intent      VARCHAR(100),
    layer_hit   VARCHAR(100),
    response_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_analytics_events PRIMARY KEY (id),
    CONSTRAINT fk_analytics_events_session_id_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- İndeksler
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_companies_sector_id ON companies(sector_id);
CREATE INDEX idx_sessions_user_identifier ON sessions(user_identifier);
CREATE INDEX idx_blogs_is_published ON blogs(is_published);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_analytics_events_session_id ON analytics_events(session_id);
CREATE INDEX idx_qa_embeddings_intent_id ON qa_embeddings(intent_id);

-- Transcript View (Yeni basitleştirilmiş yapıya göre mesajlardan birleştirir)
CREATE VIEW session_transcripts AS
SELECT
    c.session_id,
    string_agg(m.role || ': ' || m.content, E'\n' ORDER BY m.created_at, m.id) AS transcript
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
GROUP BY c.session_id;
