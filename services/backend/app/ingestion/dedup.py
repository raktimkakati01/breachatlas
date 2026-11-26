"""Deduplicate candidates against existing breaches (same organization + close dates)."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Breach

DEFAULT_WINDOW_DAYS = 14


def find_duplicate(
    db: Session, organization: str, disclosed: date, *, window_days: int = DEFAULT_WINDOW_DAYS
) -> Breach | None:
    """Return an existing breach for the same org within +/- window_days, else None."""
    candidates = db.scalars(
        select(Breach).where(func.lower(Breach.organization) == organization.strip().lower())
    ).all()
    window = timedelta(days=window_days)
    for breach in candidates:
        if abs(breach.date_disclosed - disclosed) <= window:
            return breach
    return None
