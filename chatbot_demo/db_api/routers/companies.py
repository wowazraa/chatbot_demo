from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import Company, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=Page)
def list_companies(
    sector_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Company).order_by(Company.id)
    if sector_id is not None:
        q = q.filter(Company.sector_id == sector_id)
    items, total = paginate(q, limit, offset)
    return Page(items=[CompanyOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    row = db.get(Company, company_id)
    if not row:
        raise not_found("company")
    return row
