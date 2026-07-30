"""POST /api/chat — DB kurgusuna göre chatbot turu.

Zorunlu:
  istek  → message (+ isteğe session_id)
  cevap  → reply + url (intents.url) + session_id
  yazılan → sessions / conversations / messages (+ analytics)
"""

from __future__ import annotations

import time
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db_api.bridge import Intent, get_db
from db_api.chat_persist import persist_chat_turn
from db_api.schemas import ChatLogRequest, ChatTurnRequest, ChatTurnResponse

router = APIRouter(tags=["chat"])

# Sektör key'leri intent_router_contract.map_sector()'un döndürdüğü
# (Türkçe/ASCII) değerlerle ve db_api/routers/seed.py'de tanımlanan
# intent_code'larla birebir eşleşmelidir.
_SECTOR_INTENT_CODE: dict[str, str] = {
    "saglik":  "health_appointment",
    "turizm":  "tourism_hotel",
    "eglence": "eglence_streaming",
    "egitim":  "education_enrollment",
    "bilisim": "bilisim_integration",
}

_SECTOR_TR: dict[str, str] = {
    "saglik":  "sağlık",
    "turizm":  "turizm",
    "eglence": "eğlence",
    "egitim":  "eğitim",
    "bilisim": "bilişim",
}


@lru_cache(maxsize=1)
def _get_bot():
    from src.chatbot import Chatbot
    from src.embedder import reset_embedder

    reset_embedder()
    return Chatbot(force_simulated_rewriter=True)


def _lookup_url(db: Session, sector: str, st: str) -> str | None:
    if st != "SUCCESS" or sector == "ood":
        return None
    code = _SECTOR_INTENT_CODE.get(sector)
    if not code:
        return None
    row = db.query(Intent).filter_by(intent_code=code).first()
    return row.url if row else None


def _build_reply(st: str, sector: str, url: str | None) -> str:
    if st == "SUCCESS" and url:
        tr = _SECTOR_TR.get(sector, sector)
        return (
            f"Talebinizi {tr} sektörüyle ilişkilendirdim. "
            f"İlgili forma buradan ulaşabilirsiniz: {url}"
        )
    if st == "SUCCESS":
        tr = _SECTOR_TR.get(sector, sector)
        return f"Talebinizi {tr} sektörüyle ilişkilendirdim."
    if st == "UNCERTAIN":
        return (
            "Talebinizi net anlayamadım. Hangi sektör / süreç için "
            "destek aradığınızı kısaca yazar mısınız?"
        )
    return (
        "Bu konu şu anki B2B hizmet kapsamımız dışındadır. "
        "Bilişim, eğitim, eğlence, sağlık veya turizm alanlarındaki talepleriniz için yardımcı olabilirim."
    )


import re

def sanitize_input(query: str) -> str:
    # Kelime sonlarındaki 2 veya daha fazla tekrar eden harfleri 1 harfe indirger
    # Örn: "selamm" -> "selam", "hiii" -> "hi", "booking" -> "booking" (kelime içindekilere dokunmaz)
    return re.sub(r'(\w)\1+(?=\s|$)', r'\1', query.strip())


@router.post("/chat", response_model=ChatTurnResponse, status_code=status.HTTP_200_OK)
def chat_turn(body: ChatTurnRequest, db: Session = Depends(get_db)):
    msg = sanitize_input(body.clean_message)
    if not msg:
        raise HTTPException(400, "message or query is required")

    t0 = time.perf_counter()
    try:
        bot = _get_bot()
        sid_key = f"api-{body.session_id}" if body.session_id else f"api-{body.user_identifier}"
        resp = bot.sor(msg, session_id=sid_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"router unavailable: {exc}") from exc

    latency_ms = int(round((time.perf_counter() - t0) * 1000))
    router_json = resp.to_intent_router(latency_ms=latency_ms)
    intent = router_json["intent"]
    st = router_json["status"]
    sector = intent["sector"]
    url = _lookup_url(db, sector, st)
    reply = _build_reply(st, sector, url)

    # messages.intent / confidence / response_ms kolonlarına yaz (HTTP'de şart değil)
    saved = persist_chat_turn(
        db,
        ChatLogRequest(
            user_identifier=body.user_identifier,
            session_name="chat-api",
            session_id=body.session_id,
            user_message=msg,
            bot_message=reply,
            intent=intent.get("sub_intent"),
            layer_hit=resp.mod,
            confidence=float(intent.get("confidence_score") or 0),
            response_ms=latency_ms,
            source="api",
        ),
    )

    return ChatTurnResponse(
        reply=reply,
        url=url,
        session_id=saved.session_id,
    )
