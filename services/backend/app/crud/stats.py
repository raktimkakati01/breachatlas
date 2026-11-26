"""Live homepage statistics, computed from published breaches only."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Breach, BreachControl, Control
from app.models.enums import RootCauseStatus
from app.schemas.schemas import StatsOut


def get_stats(db: Session) -> StatsOut:
    published = Breach.is_published.is_(True)

    breaches_tracked = db.scalar(select(func.count()).select_from(Breach).where(published)) or 0
    records_exposed = (
        db.scalar(select(func.coalesce(func.sum(Breach.records_affected), 0)).where(published)) or 0
    )
    countries = db.scalar(select(func.count(func.distinct(Breach.country))).where(published)) or 0
    organizations = (
        db.scalar(select(func.count(func.distinct(Breach.organization))).where(published)) or 0
    )

    most_common_row = db.execute(
        select(Control.name, func.count(BreachControl.breach_id).label("n"))
        .join(BreachControl, BreachControl.control_id == Control.id)
        .join(Breach, Breach.id == BreachControl.breach_id)
        .where(published)
        .group_by(Control.id)
        .order_by(func.count(BreachControl.breach_id).desc())
        .limit(1)
    ).first()
    most_common_missing_control = most_common_row[0] if most_common_row else None

    undisclosed = (
        db.scalar(
            select(func.count())
            .select_from(Breach)
            .where(published, Breach.root_cause_status == RootCauseStatus.undisclosed)
        )
        or 0
    )
    pct_undisclosed = round(100.0 * undisclosed / breaches_tracked, 1) if breaches_tracked else 0.0

    return StatsOut(
        breaches_tracked=breaches_tracked,
        records_exposed=int(records_exposed),
        countries=countries,
        organizations=organizations,
        most_common_missing_control=most_common_missing_control,
        pct_undisclosed_root_cause=pct_undisclosed,
    )
