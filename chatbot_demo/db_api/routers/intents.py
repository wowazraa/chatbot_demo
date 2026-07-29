from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import Intent, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import IntentOut

router = APIRouter(prefix="/intents", tags=["intents"])


@router.get("", response_model=Page)
def list_intents(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = paginate(db.query(Intent).order_by(Intent.id), limit, offset)
    return Page(items=[IntentOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/by-code/{intent_code}", response_model=IntentOut)
def get_intent_by_code(intent_code: str, db: Session = Depends(get_db)):
    row = db.query(Intent).filter_by(intent_code=intent_code).first()
    if not row:
        raise not_found("intent")
    return row


@router.get("/{intent_id}", response_model=IntentOut)
def get_intent(intent_id: int, db: Session = Depends(get_db)):
    row = db.get(Intent, intent_id)
    if not row:
        raise not_found("intent")
    return row
