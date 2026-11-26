"""Shared API dependencies: current user and role-based authorization."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.session import user_for_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole

_UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise _UNAUTHORIZED
    user = user_for_token(db, token)
    if user is None:
        raise _UNAUTHORIZED
    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory: allow only the given roles (admin is allowed implicitly)."""
    allowed = set(roles) | {UserRole.admin}

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges"
            )
        return user

    return _dep
