"""Admin user management (admin role only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_role
from app.crud.audit import write_audit
from app.crud.user import create_user, get_user_by_email, list_users
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.admin import UserCreateIn, UserOut

router = APIRouter(prefix="/users", tags=["admin:users"])


@router.get("", response_model=list[UserOut])
def list_all(
    _admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    return list_users(db)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: UserCreateIn,
    request: Request,
    admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    if get_user_by_email(db, payload.email.lower()) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = create_user(db, email=payload.email, password=payload.password, role=payload.role)
    write_audit(
        db,
        actor=admin,
        action="user.create",
        target_type="user",
        target_id=user.email,
        ip=get_client_ip(request),
        detail=f"role={user.role.value}",
    )
    return user
