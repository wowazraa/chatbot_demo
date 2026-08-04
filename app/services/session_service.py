"""Oturum yönetimi — bellek içi pipeline state + PostgreSQL kalıcılık."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import AnalyticsEvent, ChatSession, Conversation, Message
from app.schemas import ChatLogRequest, ChatLogResponse


def ensure_chat_session(
    db: Session,
    *,
    session_id: int | None,
    user_identifier: str,
    session_name: str,
) -> int:
    """DB session satırını getir veya oluştur (flush; commit persist_chat_turn'de)."""
    if session_id is not None:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(400, "session_id not found")
        return session.id

    session = ChatSession(
        session_name=session_name or f"chat-{user_identifier}",
        user_identifier=user_identifier,
        status="active",
    )
    db.add(session)
    db.flush()
    return session.id


class SessionService:
    """Pipeline bellek içi sektör hafızası (Redis yerine process-local)."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, str | None]] = {}

    def get_state(self, session_id: str | None) -> dict[str, str | None] | None:
        if not session_id:
            return None
        if session_id not in self._sessions:
            self._sessions[session_id] = {"aktif_sektor": None}
        return self._sessions[session_id]

    def get_aktif_sektor(self, session_id: str | None) -> str | None:
        state = self.get_state(session_id)
        if not state:
            return None
        return state.get("aktif_sektor")

    def set_aktif_sektor(self, session_id: str | None, sektor: str) -> None:
        if not session_id or not sektor or sektor in ("", "belirsiz", "?"):
            return
        state = self.get_state(session_id)
        if state:
            state["aktif_sektor"] = str(sektor)
        else:
            self._sessions[session_id] = {"aktif_sektor": str(sektor)}

    def clear(self, session_id: str | None) -> None:
        if session_id and session_id in self._sessions:
            del self._sessions[session_id]


def persist_chat_turn(db: Session, body: ChatLogRequest) -> ChatLogResponse:
    """Tek tur: session → conversation → user/bot message → analytics."""
    resolved_session_id = ensure_chat_session(
        db,
        session_id=body.session_id,
        user_identifier=body.user_identifier,
        session_name=body.session_name or f"chat-{body.user_identifier}",
    )
    session = db.get(ChatSession, resolved_session_id)
    assert session is not None

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


__all__ = ["SessionService", "ensure_chat_session", "persist_chat_turn"]
