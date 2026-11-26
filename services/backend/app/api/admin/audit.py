"""Audit-log viewer (admin role only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.crud.audit import list_audit
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.admin import AuditLogOut

router = APIRouter(prefix="/audit", tags=["admin:audit"])


@router.get("", response_model=list[AuditLogOut])
def read_audit(
    _admin: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list:
    return list_audit(db, limit=limit, offset=offset)
