from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import ChatSession, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import SessionOut, TranscriptOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=Page)
def list_sessions(
    user_identifier: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(ChatSession).order_by(ChatSession.id.desc())
    if user_identifier:
        q = q.filter(ChatSession.user_identifier == user_identifier)
    items, total = paginate(q, limit, offset)
    return Page(items=[SessionOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    row = db.get(ChatSession, session_id)
    if not row:
        raise not_found("session")
    return row


@router.get("/{session_id}/transcript", response_model=TranscriptOut)
def get_transcript(session_id: int, db: Session = Depends(get_db)):
    row = db.get(ChatSession, session_id)
    if not row:
        raise not_found("session")
    # view: session_transcripts
    from sqlalchemy import text

    result = db.execute(
        text("SELECT transcript FROM session_transcripts WHERE session_id = :sid"),
        {"sid": session_id},
    ).first()
    transcript = result[0] if result else ""
    return TranscriptOut(session_id=session_id, transcript=transcript or "")
