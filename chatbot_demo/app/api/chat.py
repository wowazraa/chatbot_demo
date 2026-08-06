"""POST /api/chat — ana sohbet endpoint'i."""

from __future__ import annotations

import re
import time
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_chat_db
from app.schemas import ChatLogRequest, ChatTurnRequest, ChatTurnResponse
from app.services.fallback_service import build_chat_reply, normalize_reply_lang
from app.services.intent_url_service import resolve_intent_url
from app.services.session_service import ensure_chat_session, persist_chat_turn
from app.services.shadow_read_service import maybe_schedule_shadow_read

router = APIRouter(tags=["chat"])


@lru_cache(maxsize=1)
def _get_bot():
    from app.services.embedder import reset_embedder
    from app.services.pipeline_service import V2IntentPipeline

    reset_embedder()
    return V2IntentPipeline()


def sanitize_input(query: str) -> str:
    return re.sub(r"(\w)\1{2,}(?=\s|$)", r"\1", query.strip())


@router.post("/chat", response_model=ChatTurnResponse, status_code=status.HTTP_200_OK)
def chat_turn(body: ChatTurnRequest, db: Session = Depends(get_chat_db)):
    msg = sanitize_input(body.clean_message)
    if not msg:
        raise HTTPException(400, "message or query is required")

    session_name = body.external_session_id or "chat-api"
    db_session_id = ensure_chat_session(
        db,
        session_id=body.session_id,
        user_identifier=body.user_identifier,
        session_name=session_name,
    )
    if body.external_session_id:
        pipeline_session_id = f"ext-{body.external_session_id}"
    else:
        pipeline_session_id = f"api-{db_session_id}"

    reply_lang = normalize_reply_lang(body.lang)
    force_lang = reply_lang if body.lang else None

    t0 = time.perf_counter()
    try:
        bot = _get_bot()
        resp = bot.run(msg, session_id=pipeline_session_id, force_lang=force_lang)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"router unavailable: {exc}") from exc

    latency_ms = int(round((time.perf_counter() - t0) * 1000))
    layer = resp.layer
    st = resp.status
    sector = resp.sector
    sub_intent = resp.sub_intent
    confidence = float(resp.confidence_score)

    if not body.lang:
        reply_lang = normalize_reply_lang(resp.detected_language)

    url = resolve_intent_url(sector, st)
    if st == "INFO" and resp.response_message:
        reply = resp.response_message
        url = None  # Kurumsal/BILGI — yalnızca metin, link yok
    elif sector == "ood" and layer == "rule" and resp.response_message:
        reply = resp.response_message
    else:
        reply = build_chat_reply(st, sector, url, lang=reply_lang)

    saved = persist_chat_turn(
        db,
        ChatLogRequest(
            user_identifier=body.user_identifier,
            session_name=session_name,
            session_id=db_session_id,
            user_message=msg,
            bot_message=reply,
            intent=sub_intent,
            layer_hit=layer,
            confidence=confidence,
            response_ms=latency_ms,
            source="api",
        ),
    )

    maybe_schedule_shadow_read(
        query=msg,
        local_sector=sector,
        local_status=st,
        local_confidence=confidence,
        local_layer=layer,
    )

    return ChatTurnResponse(
        reply=reply,
        url=url,
        session_id=saved.session_id,
    )
