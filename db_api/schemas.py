"""Pydantic istek/yanıt modelleri (v6 şema ile uyumlu)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EMBEDDING_DIM = 1024


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SectorCreate(BaseModel):
    sector_key: str = Field(..., max_length=50)
    sector_name_tr: str = Field(..., max_length=100)
    sector_name_en: str = Field(..., max_length=100)


class SectorUpdate(BaseModel):
    sector_name_tr: str | None = Field(None, max_length=100)
    sector_name_en: str | None = Field(None, max_length=100)


class SectorOut(OrmBase):
    id: int
    sector_key: str
    sector_name_tr: str
    sector_name_en: str
    created_at: datetime


class IntentCreate(BaseModel):
    intent_code: str = Field(..., max_length=100)
    url: str = Field(..., max_length=500)
    description: str | None = None


class IntentUpdate(BaseModel):
    url: str | None = Field(None, max_length=500)
    description: str | None = None


class IntentOut(OrmBase):
    id: int
    intent_code: str
    url: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CompanyCreate(BaseModel):
    company_name: str = Field(..., max_length=255)
    sector_id: int | None = None


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=255)
    sector_id: int | None = None


class CompanyOut(OrmBase):
    id: int
    company_name: str
    sector_id: int | None
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    username: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    role: Literal["admin", "editor"] = "editor"
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    email: str | None = Field(None, max_length=255)
    password: str | None = Field(None, min_length=6)
    role: Literal["admin", "editor"] | None = None
    is_active: bool | None = None


class AdminUserOut(OrmBase):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BlogCreate(BaseModel):
    slug: str = Field(..., max_length=255)
    title_tr: str = Field(..., max_length=255)
    title_en: str = Field(..., max_length=255)
    content_tr: str
    content_en: str
    is_published: bool = False
    published_at: datetime | None = None
    author_id: int | None = None


class BlogUpdate(BaseModel):
    slug: str | None = Field(None, max_length=255)
    title_tr: str | None = Field(None, max_length=255)
    title_en: str | None = Field(None, max_length=255)
    content_tr: str | None = None
    content_en: str | None = None
    is_published: bool | None = None
    published_at: datetime | None = None
    author_id: int | None = None


class BlogOut(OrmBase):
    id: int
    slug: str
    title_tr: str
    title_en: str
    content_tr: str
    content_en: str
    is_published: bool
    published_at: datetime | None
    author_id: int | None
    created_at: datetime
    updated_at: datetime


class SessionCreate(BaseModel):
    session_name: str = Field(..., max_length=255)
    user_identifier: str = Field(..., max_length=255)
    status: Literal["active", "closed", "expired"] = "active"
    closed_at: datetime | None = None


class SessionUpdate(BaseModel):
    session_name: str | None = Field(None, max_length=255)
    status: Literal["active", "closed", "expired"] | None = None
    closed_at: datetime | None = None


class SessionOut(OrmBase):
    id: int
    session_name: str
    user_identifier: str
    status: str
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TranscriptOut(BaseModel):
    session_id: int
    transcript: str | None


class ConversationCreate(BaseModel):
    session_id: int


class ConversationOut(OrmBase):
    id: int
    session_id: int
    created_at: datetime


class MessageCreate(BaseModel):
    conversation_id: int
    content: str
    role: Literal["user", "bot"]
    intent: str | None = Field(None, max_length=100)
    source: str | None = Field("web", max_length=100)
    confidence: float | None = None
    response_ms: int | None = None


class MessageUpdate(BaseModel):
    content: str | None = None
    intent: str | None = Field(None, max_length=100)
    source: str | None = Field(None, max_length=100)
    confidence: float | None = None
    response_ms: int | None = None


class MessageOut(OrmBase):
    id: int
    conversation_id: int
    content: str
    role: str
    intent: str | None
    source: str | None
    confidence: float | None
    response_ms: int | None
    created_at: datetime


class ChatMessageOut(OrmBase):
    """Chatbot GET /messages — messages.role + messages.content."""

    role: str
    content: str


class QaCreate(BaseModel):
    question: str
    answer: str
    intent_id: int
    is_augmented: bool = False
    embedding: list[float] = Field(..., min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM)


class QaUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    intent_id: int | None = None
    is_augmented: bool | None = None
    embedding: list[float] | None = Field(None, min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM)


class QaOut(OrmBase):
    id: int
    question: str
    answer: str
    intent_id: int
    is_augmented: bool
    created_at: datetime


class QaOutWithEmbedding(QaOut):
    embedding: list[float]


class QaSearchRequest(BaseModel):
    embedding: list[float] = Field(..., min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM)
    limit: int = Field(5, ge=1, le=50)
    intent_id: int | None = None


class QaSearchHit(BaseModel):
    id: int
    question: str
    answer: str
    intent_id: int
    distance: float


class AnalyticsEventCreate(BaseModel):
    session_id: int
    intent: str | None = Field(None, max_length=100)
    layer_hit: str | None = Field(None, max_length=100)
    response_ms: int | None = None


class AnalyticsEventOut(OrmBase):
    id: int
    session_id: int
    intent: str | None
    layer_hit: str | None
    response_ms: int | None
    created_at: datetime


class AnalyticsSummary(BaseModel):
    total_events: int
    by_layer_hit: dict[str, int]
    by_intent: dict[str, int]
    avg_response_ms: float | None


class ChatLogRequest(BaseModel):
    user_identifier: str = Field(..., max_length=255)
    session_name: str | None = Field(None, max_length=255)
    session_id: int | None = None
    conversation_id: int | None = None
    user_message: str
    bot_message: str
    intent: str | None = Field(None, max_length=100)
    layer_hit: str | None = Field(None, max_length=100)
    confidence: float | None = None
    response_ms: int | None = None
    source: str = "web"


class ChatLogResponse(BaseModel):
    session_id: int
    conversation_id: int
    user_message_id: int
    bot_message_id: int
    analytics_event_id: int


class ChatTurnRequest(BaseModel):
    """Kullanıcı mesajı (sessions / messages yazımı için)."""

    message: str | None = Field(None, min_length=1)
    query: str | None = Field(None, min_length=1)
    session_id: int | None = None
    user_identifier: str = Field("web-user", max_length=255)

    @property
    def clean_message(self) -> str:
        return (self.message or self.query or "").strip()


class ChatTurnResponse(BaseModel):
    """DB zorunluları: bot cevabı + intents.url + sessions.id."""

    reply: str
    url: str | None
    session_id: int


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    ok: bool
    admin_id: int
    username: str
    role: str
    message: str = "login ok"


class SeedResponse(BaseModel):
    sectors_upserted: int
    intents_upserted: int
    companies_upserted: int
    admin_upserted: bool
    blogs_upserted: int
    qa_upserted: int
    sample_session_id: int | None = None
    ids: dict[str, int | None] = {}
    detail: str = "seed complete"


class ApiCatalogItem(BaseModel):
    method: str
    path: str
    name: str | None = None
    tags: list[str] = []
