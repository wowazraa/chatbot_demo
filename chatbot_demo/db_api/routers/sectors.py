from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import Sector, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import SectorOut

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", response_model=Page)
def list_sectors(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = paginate(db.query(Sector).order_by(Sector.id), limit, offset)
    return Page(items=[SectorOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/{sector_id}", response_model=SectorOut)
def get_sector(sector_id: int, db: Session = Depends(get_db)):
    row = db.get(Sector, sector_id)
    if not row:
        raise not_found("sector")
    return row
