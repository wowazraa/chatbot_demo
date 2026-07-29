"""Chatbot / Bilgi Merkezi Projesi — SQLAlchemy modelleri (v6 - Sadeleştirilmiş). Bkz. schema.sql."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
    MetaData,
    event,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 1024
SUPPORTED_LANGUAGES = frozenset({"tr", "en"})

# Standartlaştırılmış kısıt ve dizin isimlendirme şeması (Alembic autogenerate çakışmalarını önlemek için)
convention = {
    "ix": "idx_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


class Sector(Base):
    __tablename__ = "sectors"
    __table_args__ = (
        UniqueConstraint("sector_key", name="uq_sectors_sector_key"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    sector_key: Mapped[str] = mapped_column(String(50), nullable=False)
    sector_name_tr: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    companies: Mapped[list["Company"]] = relationship(back_populates="sector")


class Intent(Base):
    __tablename__ = "intents"
    __table_args__ = (
        UniqueConstraint("intent_code", name="uq_intents_intent_code"),
        CheckConstraint("BTRIM(intent_code) <> ''", name="ck_intents_intent_code_not_blank"),
        CheckConstraint("BTRIM(url) <> ''", name="ck_intents_url_not_blank"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    intent_code: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    qa_embeddings: Mapped[list["QaEmbedding"]] = relationship(back_populates="intent", passive_deletes=True)


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_admin_users_username"),
        UniqueConstraint("email", name="uq_admin_users_email"),
        CheckConstraint("role IN ('admin', 'editor')", name="ck_admin_users_role"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="editor", server_default=text("'editor'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    blogs: Mapped[list["Blog"]] = relationship(back_populates="author")


class Blog(Base):
    __tablename__ = "blogs"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_blogs_slug"),
        CheckConstraint(
            "(is_published = false) OR (is_published = true AND published_at IS NOT NULL)",
            name="ck_blogs_publish_consistency",
        ),
        Index("idx_blogs_is_published", "is_published"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title_tr: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    content_tr: Mapped[str] = mapped_column(Text, nullable=False)
    content_en: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL", name="fk_blogs_author_id_admin_users"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["AdminUser | None"] = relationship(back_populates="blogs")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("company_name", name="uq_companies_company_name"),
        Index("idx_companies_sector_id", "sector_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectors.id", ondelete="SET NULL", name="fk_companies_sector_id_sectors"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sector: Mapped["Sector | None"] = relationship(back_populates="companies")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed', 'expired')", name="ck_sessions_status"),
        CheckConstraint(
            "(status = 'active' AND closed_at IS NULL) "
            "OR (status IN ('closed', 'expired') AND closed_at IS NOT NULL)",
            name="ck_sessions_closed_at_consistency",
        ),
        Index("idx_sessions_user_identifier", "user_identifier"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default=text("'active'"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analytics_events: Mapped[list["AnalyticsEvent"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE", name="fk_conversations_session_id_sessions"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'bot')", name="ck_messages_role"),
        Index("idx_messages_conversation_id", "conversation_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE", name="fk_messages_conversation_id_conversations"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100), default="web", server_default=text("'web'"))
    confidence: Mapped[float | None] = mapped_column(Float)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class QaEmbedding(Base):
    __tablename__ = "qa_embeddings"
    __table_args__ = (
        Index("idx_qa_embeddings_intent_id", "intent_id"),
        CheckConstraint("BTRIM(question) <> ''", name="ck_qa_embeddings_question_not_blank"),
        CheckConstraint("BTRIM(answer) <> ''", name="ck_qa_embeddings_answer_not_blank"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    intent_id: Mapped[int] = mapped_column(ForeignKey("intents.id", ondelete="RESTRICT", name="fk_qa_embeddings_intent_id_intents"), nullable=False)
    is_augmented: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    intent: Mapped["Intent"] = relationship(back_populates="qa_embeddings")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("idx_analytics_events_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE", name="fk_analytics_events_session_id_sessions"), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100))
    layer_hit: Mapped[str | None] = mapped_column(String(100))
    response_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="analytics_events")


# Nesne bazlı doğrulamalar (Alan atama sırasından etkilenmeyen event listener'lar)
@event.listens_for(Blog, "before_insert")
@event.listens_for(Blog, "before_update")
def validate_blog_consistency(mapper, connection, target):
    if target.is_published and target.published_at is None:
        raise ValueError("published_at is required when is_published is True")


@event.listens_for(Session, "before_insert")
@event.listens_for(Session, "before_update")
def validate_session_consistency(mapper, connection, target):
    if target.status == "active" and target.closed_at is not None:
        raise ValueError("closed_at must be NULL when status is 'active'")
    if target.status in ("closed", "expired") and target.closed_at is None:
        raise ValueError(f"closed_at is required when status is '{target.status}'")
