"""Konuşma kalıcılığı — HTTP yerine iç fonksiyon.

Session / conversation / message / analytics satırlarını burada yazar.
Dışarıya: POST /api/chat/log + GET /api/messages yeter.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db_api.bridge import AnalyticsEvent, ChatSession, Conversation, Message
from db_api.schemas import ChatLogRequest, ChatLogResponse


def persist_chat_turn(db: Session, body: ChatLogRequest) -> ChatLogResponse:
    """Tek tur: session (+gerekirse) → conversation → user/bot message → analytics."""
    if body.session_id is not None:
        session = db.get(ChatSession, body.session_id)
        if not session:
            raise HTTPException(400, "session_id not found")
    else:
        session = ChatSession(
            session_name=body.session_name or f"chat-{body.user_identifier}",
            user_identifier=body.user_identifier,
            status="active",
        )
        db.add(session)
        db.flush()

    if body.conversation_id is not None:
        conv = db.get(Conversation, body.conversation_id)
        if not conv or conv.session_id != session.id:
            raise HTTPException(400, "conversation_id invalid for session")
    else:
        conv = Conversation(session_id=session.id)
        db.add(conv)
        db.flush()

    user_msg = Message(
        conversation_id=conv.id,
        content=body.user_message,
        role="user",
        intent=body.intent,
        source=body.source,
        confidence=body.confidence,
    )
    bot_msg = Message(
        conversation_id=conv.id,
        content=body.bot_message,
        role="bot",
        intent=body.intent,
        source=body.source,
        confidence=body.confidence,
        response_ms=body.response_ms,
    )
    event = AnalyticsEvent(
        session_id=session.id,
        intent=body.intent,
        layer_hit=body.layer_hit,
        response_ms=body.response_ms,
    )
    db.add_all([user_msg, bot_msg, event])
    try:
        db.commit()
        db.refresh(user_msg)
        db.refresh(bot_msg)
        db.refresh(event)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(400, f"db error: {exc}") from exc

    return ChatLogResponse(
        session_id=session.id,
        conversation_id=conv.id,
        user_message_id=user_msg.id,
        bot_message_id=bot_msg.id,
        analytics_event_id=event.id,
    )
