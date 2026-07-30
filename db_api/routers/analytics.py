from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from db_api.bridge import AnalyticsEvent, get_db
from db_api.chat_persist import persist_chat_turn
from db_api.schemas import AnalyticsSummary, ChatLogRequest, ChatLogResponse

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(AnalyticsEvent.id)).scalar() or 0
    by_layer: dict[str, int] = {}
    for layer, cnt in (
        db.query(AnalyticsEvent.layer_hit, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.layer_hit)
        .all()
    ):
        by_layer[layer or "null"] = cnt
    by_intent: dict[str, int] = {}
    for intent, cnt in (
        db.query(AnalyticsEvent.intent, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.intent)
        .all()
    ):
        by_intent[intent or "null"] = cnt
    avg_ms = db.query(func.avg(AnalyticsEvent.response_ms)).scalar()
    return AnalyticsSummary(
        total_events=total,
        by_layer_hit=by_layer,
        by_intent=by_intent,
        avg_response_ms=float(avg_ms) if avg_ms is not None else None,
    )


@router.post("/chat/log", response_model=ChatLogResponse, status_code=status.HTTP_201_CREATED)
def chat_log(body: ChatLogRequest, db: Session = Depends(get_db)):
    """Yazma tek kapı: içeride session/conversation/message/analytics fonksiyonla yazılır."""
    return persist_chat_turn(db, body)
