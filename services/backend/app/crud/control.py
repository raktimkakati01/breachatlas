"""Read queries for controls and control pages (e.g. 'MFA' → every breach it was a factor in)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Breach, BreachControl, Control


def list_controls(db: Session) -> list[Control]:
    return list(db.scalars(select(Control).order_by(Control.name)).all())


def get_control_page(
    db: Session, slug: str, *, limit: int = 20, offset: int = 0
) -> tuple[Control, list[Breach], int] | None:
    control = db.scalar(select(Control).where(Control.slug == slug))
    if control is None:
        return None

    stmt = (
        select(Breach)
        .join(BreachControl, BreachControl.breach_id == Breach.id)
        .where(BreachControl.control_id == control.id, Breach.is_published.is_(True))
        .order_by(Breach.date_disclosed.desc())
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    breaches = list(db.scalars(stmt.limit(limit).offset(offset)).all())
    return control, breaches, total
