"""initial complete schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-07-20 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create extension vector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Create trigger functions
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Create tables
    # sectors
    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("sector_key", sa.String(length=50), nullable=False),
        sa.Column("sector_name_tr", sa.String(length=100), nullable=False),
        sa.Column("sector_name_en", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sectors"),
        sa.UniqueConstraint("sector_key", name="uq_sectors_sector_key")
    )

    # intents
    op.create_table(
        "intents",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("intent_code", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_intents"),
        sa.UniqueConstraint("intent_code", name="uq_intents_intent_code"),
        sa.CheckConstraint("BTRIM(intent_code) <> ''", name="ck_intents_intent_code_not_blank"),
        sa.CheckConstraint("BTRIM(url) <> ''", name="ck_intents_url_not_blank")
    )

    # admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="'editor'", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'editor')", name="ck_admin_users_role"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_users"),
        sa.UniqueConstraint("username", name="uq_admin_users_username"),
        sa.UniqueConstraint("email", name="uq_admin_users_email")
    )

    # blogs
    op.create_table(
        "blogs",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title_tr", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("content_tr", sa.Text(), nullable=False),
        sa.Column("content_en", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("(is_published = false) OR (is_published = true AND published_at IS NOT NULL)", name="ck_blogs_publish_consistency"),
        sa.ForeignKeyConstraint(["author_id"], ["admin_users.id"], name="fk_blogs_author_id_admin_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_blogs"),
        sa.UniqueConstraint("slug", name="uq_blogs_slug")
    )
    op.create_index("idx_blogs_is_published", "blogs", ["is_published"])

    # companies
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("sector_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], name="fk_companies_sector_id_sectors", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("company_name", name="uq_companies_company_name")
    )
    op.create_index("idx_companies_sector_id", "companies", ["sector_id"])

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("session_name", sa.String(length=255), nullable=False),
        sa.Column("user_identifier", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="'active'", nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'closed', 'expired')", name="ck_sessions_status"),
        sa.CheckConstraint("(status = 'active' AND closed_at IS NULL) OR (status IN ('closed', 'expired') AND closed_at IS NOT NULL)", name="ck_sessions_closed_at_consistency"),
        sa.PrimaryKeyConstraint("id", name="pk_sessions")
    )
    op.create_index("idx_sessions_user_identifier", "sessions", ["user_identifier"])

    # conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_conversations_session_id_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations")
    )
    op.create_index("idx_conversations_session_id", "conversations", ["session_id"])

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("intent", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="'web'", nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('user', 'bot')", name="ck_messages_role"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_messages")
    )
    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"])

    # qa_embeddings
    op.create_table(
        "qa_embeddings",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("intent_id", sa.Integer(), nullable=False),
        sa.Column("is_augmented", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=False),
        sa.CheckConstraint("BTRIM(question) <> ''", name="ck_qa_embeddings_question_not_blank"),
        sa.CheckConstraint("BTRIM(answer) <> ''", name="ck_qa_embeddings_answer_not_blank"),
        sa.ForeignKeyConstraint(["intent_id"], ["intents.id"], name="fk_qa_embeddings_intent_id_intents", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_qa_embeddings")
    )
    op.create_index("idx_qa_embeddings_intent_id", "qa_embeddings", ["intent_id"])

    # analytics_events
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("intent", sa.String(length=100), nullable=True),
        sa.Column("layer_hit", sa.String(length=100), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_analytics_events_session_id_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_events")
    )
    op.create_index("idx_analytics_events_session_id", "analytics_events", ["session_id"])

    # 4. Create trigger bindings on PostgreSQL
    op.execute("""
        CREATE TRIGGER trg_intents_updated_at BEFORE UPDATE ON intents
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_users_updated_at BEFORE UPDATE ON admin_users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
    op.execute("""
        CREATE TRIGGER trg_blogs_updated_at BEFORE UPDATE ON blogs
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
    op.execute("""
        CREATE TRIGGER trg_companies_updated_at BEFORE UPDATE ON companies
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
    op.execute("""
        CREATE TRIGGER trg_sessions_updated_at BEFORE UPDATE ON sessions
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # 5. Create View
    op.execute("""
        CREATE VIEW session_transcripts AS
        SELECT
            c.session_id,
            string_agg(m.role || ': ' || m.content, E'\\n' ORDER BY m.created_at, m.id) AS transcript
        FROM conversations c
        JOIN messages m ON m.conversation_id = c.id
        GROUP BY c.session_id;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS session_transcripts")
    op.drop_table("analytics_events")
    op.execute("DROP INDEX IF EXISTS idx_qa_embeddings_intent_id")
    op.drop_table("qa_embeddings")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("sessions")
    op.drop_table("companies")
    op.drop_table("blogs")
    op.drop_table("admin_users")
    op.drop_table("intents")
    op.drop_table("sectors")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
