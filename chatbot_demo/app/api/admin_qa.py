import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_allintos_db, Intent, QaEmbedding, EMBEDDING_DIM

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    token = os.getenv("ADMIN_API_TOKEN", "super-secret")
    if not auth_header or auth_header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


class CreateQaEmbeddingRequest(BaseModel):
    question: str
    answer: str
    intent_id: int
    is_augmented: bool = False


class UpdateQaEmbeddingRequest(BaseModel):
    question: str | None = None
    answer: str | None = None
    intent_id: int | None = None
    is_augmented: bool | None = None


@router.post("/qa_embeddings")
def create_qa_embedding(
    req: CreateQaEmbeddingRequest,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    db_intent = db.get(Intent, req.intent_id)
    if not db_intent:
        raise HTTPException(
            status_code=400,
            detail={"intent_id": "Belirtilen intent bulunamadı."}
        )

    new_qa = QaEmbedding(
        question=req.question,
        answer=req.answer,
        intent_id=req.intent_id,
        is_augmented=req.is_augmented,
        embedding=[0.0] * EMBEDDING_DIM,
    )
    db.add(new_qa)
    try:
        db.commit()
        db.refresh(new_qa)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {
        "data": {
            "id": new_qa.id,
            "question": new_qa.question,
            "answer": new_qa.answer,
            "intent_id": new_qa.intent_id,
            "is_augmented": new_qa.is_augmented,
            "created_at": new_qa.created_at.isoformat() if new_qa.created_at else None,
        },
        "meta": {}
    }


@router.put("/qa_embeddings/{id}")
def update_qa_embedding(
    id: int,
    req: UpdateQaEmbeddingRequest,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    qa = db.get(QaEmbedding, id)
    if not qa:
        raise HTTPException(status_code=404, detail="Soru-cevap kaydı bulunamadı.")

    if req.intent_id is not None:
        intent = db.get(Intent, req.intent_id)
        if not intent:
            raise HTTPException(
                status_code=400,
                detail={"intent_id": "Belirtilen niyet bulunamadı."}
            )
        qa.intent_id = req.intent_id

    if req.question is not None:
        qa.question = req.question
    if req.answer is not None:
        qa.answer = req.answer
    if req.is_augmented is not None:
        qa.is_augmented = req.is_augmented

    try:
        db.commit()
        db.refresh(qa)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {
        "data": {
            "id": qa.id,
            "question": qa.question,
            "answer": qa.answer,
            "intent_id": qa.intent_id,
            "is_augmented": qa.is_augmented,
            "created_at": qa.created_at.isoformat() if qa.created_at else None,
        },
        "meta": {}
    }


@router.delete("/qa_embeddings/{id}")
def delete_qa_embedding(
    id: int,
    db: Session = Depends(get_allintos_db),
    _ = Depends(verify_token),
):
    qa = db.get(QaEmbedding, id)
    if not qa:
        raise HTTPException(status_code=404, detail="Soru-cevap kaydı bulunamadı.")

    db.delete(qa)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {exc}")

    return {"status": "success", "message": "Soru-cevap kaydı başarıyla silindi."}
