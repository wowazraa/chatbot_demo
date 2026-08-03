"""Ortak API yardımcıları — pagination, commit, hata."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session

T = TypeVar("T")


class Page(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


def page_params(
    limit: int = Query(50, ge=1, le=500, description="Sayfa boyutu"),
    offset: int = Query(0, ge=0, description="Atlanacak kayıt"),
) -> tuple[int, int]:
    return limit, offset


def paginate(q: SAQuery, limit: int, offset: int) -> tuple[list, int]:
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return items, total


def commit_refresh(db: Session, row: Any) -> Any:
    try:
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"db error: {exc}") from exc


def commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"db error: {exc}") from exc


def not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity} not found")
