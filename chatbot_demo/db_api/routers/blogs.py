from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db_api.bridge import Blog, get_db
from db_api.common import Page, not_found, paginate
from db_api.schemas import BlogOut

router = APIRouter(prefix="/blogs", tags=["blogs"])


@router.get("", response_model=Page)
def list_blogs(
    published_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Blog).order_by(Blog.id.desc())
    if published_only:
        q = q.filter(Blog.is_published.is_(True))
    items, total = paginate(q, limit, offset)
    return Page(items=[BlogOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)


@router.get("/by-slug/{slug}", response_model=BlogOut)
def get_blog_by_slug(slug: str, db: Session = Depends(get_db)):
    row = db.query(Blog).filter_by(slug=slug).first()
    if not row:
        raise not_found("blog")
    return row


@router.get("/{blog_id}", response_model=BlogOut)
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    row = db.get(Blog, blog_id)
    if not row:
        raise not_found("blog")
    return row
