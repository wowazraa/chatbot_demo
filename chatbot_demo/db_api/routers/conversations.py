from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import Conversation, Message, get_db
from db_api.common import Page, paginate
from db_api.schemas import ChatMessageOut

router = APIRouter(tags=["messages"])


@router.get("/messages", response_model=Page)
@router.get("/api/messages", response_model=Page)
@router.get("/status", response_model=Page)
@router.get("/api/status", response_model=Page)
def list_messages(
    conversation_id: int | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Konuşma geçmişi — zorunlu: role, content."""
    q = db.query(Message).order_by(Message.id)
    if conversation_id is not None:
        q = q.filter(Message.conversation_id == conversation_id)
    if session_id is not None and str(session_id).strip() != "" and str(session_id).strip() != "null":
        try:
            sid_int = int(session_id)
            q = q.join(Conversation, Conversation.id == Message.conversation_id).filter(
                Conversation.session_id == sid_int
            )
        except ValueError:
            # session_id bir sayı değilse eşleşme bulamaz
            q = q.filter(False)
    items, total = paginate(q, limit, offset)
    return Page(
        items=[ChatMessageOut.model_validate(x) for x in items],
        total=total,
        limit=limit,
        offset=offset,
    )
