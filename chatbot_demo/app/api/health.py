from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import use_allintos_chat_db
from app.db.database import get_chat_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_chat_db)):
    backend = "allintos" if use_allintos_chat_db() else "local"
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "chat_db": backend}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
