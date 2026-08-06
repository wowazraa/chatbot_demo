import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_allintos_db, Intent

router = APIRouter(prefix="/admin/intents", tags=["admin-intents"])


def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    token = os.getenv("ADMIN_API_TOKEN", "super-secret")
    if not auth_header or auth_header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


class CreateIntentRequest(BaseModel):
    intent_code: str
    url: str
    description: str | None = None


class UpdateIntentRequest(BaseModel):
    intent_code: str | None = None
    url: str | None = None
    description: str | None = None


@router.post("")
def create_intent(
    req: CreateIntentRequest,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    from sqlalchemy import select
    db_intent = db.scalar(select(Intent).where(Intent.intent_code == req.intent_code))
    if db_intent:
        raise HTTPException(status_code=409, detail="Bu niyet kodu zaten kullanılıyor.")

    new_intent = Intent(
        intent_code=req.intent_code,
        url=req.url,
        description=req.description,
    )
    db.add(new_intent)
    try:
        db.commit()
        db.refresh(new_intent)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {
        "data": {
            "id": new_intent.id,
            "intent_code": new_intent.intent_code,
            "url": new_intent.url,
            "description": new_intent.description,
            "created_at": new_intent.created_at.isoformat() if new_intent.created_at else None,
            "updated_at": new_intent.updated_at.isoformat() if new_intent.updated_at else None,
        },
        "meta": {}
    }


@router.put("/{id}")
def update_intent(
    id: int,
    req: UpdateIntentRequest,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    intent = db.get(Intent, id)
    if not intent:
        raise HTTPException(status_code=404, detail="Niyet bulunamadı.")

    if req.intent_code is not None:
        from sqlalchemy import select
        existing = db.scalar(select(Intent).where(Intent.intent_code == req.intent_code, Intent.id != id))
        if existing:
            raise HTTPException(status_code=409, detail="Bu niyet kodu zaten başka bir niyet tarafından kullanılıyor.")
        intent.intent_code = req.intent_code

    if req.url is not None:
        intent.url = req.url
    if req.description is not None:
        intent.description = req.description

    try:
        db.commit()
        db.refresh(intent)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {
        "data": {
            "id": intent.id,
            "intent_code": intent.intent_code,
            "url": intent.url,
            "description": intent.description,
            "created_at": intent.created_at.isoformat() if intent.created_at else None,
            "updated_at": intent.updated_at.isoformat() if intent.updated_at else None,
        },
        "meta": {}
    }


@router.delete("/{id}")
def delete_intent(
    id: int,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    from app.db.database import QaEmbedding
    intent = db.get(Intent, id)
    if not intent:
        raise HTTPException(status_code=404, detail="Niyet bulunamadı.")

    from sqlalchemy import select
    has_relations = db.scalar(select(QaEmbedding).where(QaEmbedding.intent_id == id).limit(1))
    if has_relations:
        raise HTTPException(
            status_code=400,
            detail="Bu niyete bağlı soru-cevaplar bulunduğu için silinemez. Önce ilişkili soru-cevapları silmelisiniz."
        )

    db.delete(intent)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {"status": "success", "message": "Niyet başarıyla silindi."}
