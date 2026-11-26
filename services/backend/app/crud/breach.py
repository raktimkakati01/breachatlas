"""Read queries for breaches. Only *published* breaches are ever returned publicly."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AttackStep, Breach, BreachControl


def list_breaches(
    db: Session,
    *,
    country: str | None = None,
    sector: str | None = None,
    year: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Breach], int]:
    stmt = select(Breach).where(Breach.is_published.is_(True))

    if country:
        stmt = stmt.where(Breach.country == country)
    if sector:
        stmt = stmt.where(Breach.sector == sector)
    if year:
        # Portable year filter (no EXTRACT — works on SQLite and PostgreSQL).
        stmt = stmt.where(
            Breach.date_disclosed >= date(year, 1, 1),
            Breach.date_disclosed <= date(year, 12, 31),
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Breach.organization.ilike(like))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Breach.date_disclosed.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def get_published_breach(db: Session, slug: str) -> Breach | None:
    stmt = (
        select(Breach)
        .where(Breach.slug == slug, Breach.is_published.is_(True))
        .options(
            selectinload(Breach.data_types),
            selectinload(Breach.attack_steps).selectinload(AttackStep.techniques),
            selectinload(Breach.sources),
            selectinload(Breach.control_links).selectinload(BreachControl.control),
        )
    )
    return db.scalar(stmt)
