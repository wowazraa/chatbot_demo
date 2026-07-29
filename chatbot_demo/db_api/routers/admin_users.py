import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db_api.bridge import AdminUser, get_db
from db_api.common import Page, paginate
from db_api.schemas import AdminLoginRequest, AdminLoginResponse, AdminUserOut

router = APIRouter(prefix="/admin-users", tags=["admin_users"])


def _verify(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


@router.post("/login", response_model=AdminLoginResponse)
def login(body: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter_by(username=body.username).first()
    if not user or not user.is_active or not _verify(body.password, user.password_hash):
        raise HTTPException(401, "invalid username or password")
    return AdminLoginResponse(ok=True, admin_id=user.id, username=user.username, role=user.role)


@router.get("", response_model=Page)
def list_admin_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = paginate(db.query(AdminUser).order_by(AdminUser.id), limit, offset)
    return Page(items=[AdminUserOut.model_validate(x) for x in items], total=total, limit=limit, offset=offset)
