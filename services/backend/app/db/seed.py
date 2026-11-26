"""Load the clearly-marked DEMO fixture dataset into the database.

Idempotent: reference rows are get-or-created by their natural key, and a breach whose
slug already exists is skipped. Run with:  python -m app.db.seed
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    AttackStep,
    Breach,
    BreachControl,
    ChangeLog,
    Control,
    DataType,
    Provenance,
    Source,
    Technique,
)
from app.models.enums import (
    AttackPhase,
    ConfidenceLabel,
    ConfirmationStatus,
    ControlRelationship,
    RootCauseStatus,
    SourceType,
)

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_breaches.json"


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _get_or_create_technique(db: Session, data: dict) -> Technique:
    obj = db.scalar(select(Technique).where(Technique.technique_id == data["technique_id"]))
    if obj is None:
        obj = Technique(**data)
        db.add(obj)
        db.flush()
    return obj


def _get_or_create_control(db: Session, data: dict) -> Control:
    obj = db.scalar(select(Control).where(Control.slug == data["slug"]))
    if obj is None:
        obj = Control(**data)
        db.add(obj)
        db.flush()
    return obj


def _get_or_create_data_type(db: Session, data: dict) -> DataType:
    obj = db.scalar(select(DataType).where(DataType.slug == data["slug"]))
    if obj is None:
        obj = DataType(**data)
        db.add(obj)
        db.flush()
    return obj


def load_fixtures(db: Session, path: Path = FIXTURE_PATH) -> int:
    """Load fixtures from `path`. Returns the number of breaches created."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    techniques = {t["technique_id"]: _get_or_create_technique(db, t) for t in payload["techniques"]}
    controls = {c["slug"]: _get_or_create_control(db, c) for c in payload["controls"]}
    data_types = {d["slug"]: _get_or_create_data_type(db, d) for d in payload["data_types"]}

    created = 0
    for b in payload["breaches"]:
        if db.scalar(select(Breach).where(Breach.slug == b["slug"])) is not None:
            continue  # already seeded

        breach = Breach(
            slug=b["slug"],
            organization=b["organization"],
            country=b["country"],
            sector=b["sector"],
            date_disclosed=_parse_date(b["date_disclosed"]),
            date_occurred=_parse_date(b.get("date_occurred")),
            records_affected=b.get("records_affected"),
            confirmation_status=ConfirmationStatus(b["confirmation_status"]),
            root_cause_status=RootCauseStatus(b["root_cause_status"]),
            summary=b.get("summary"),
            lessons_for_defenders=b.get("lessons_for_defenders"),
            what_users_should_do=b.get("what_users_should_do"),
            is_published=b.get("is_published", False),
        )
        breach.data_types = [data_types[s] for s in b.get("data_types", [])]

        for step in b.get("attack_steps", []):
            attack_step = AttackStep(
                step_order=step["step_order"],
                phase=AttackPhase(step["phase"]),
                description=step["description"],
                techniques=[techniques[t] for t in step.get("techniques", [])],
            )
            breach.attack_steps.append(attack_step)

        for link in b.get("controls", []):
            breach.control_links.append(
                BreachControl(
                    control=controls[link["slug"]],
                    relationship_type=ControlRelationship(link["relationship_type"]),
                )
            )

        for src in b.get("sources", []):
            breach.sources.append(
                Source(
                    url=src["url"],
                    title=src.get("title"),
                    publisher=src.get("publisher"),
                    source_type=SourceType(src["source_type"]),
                    date_retrieved=_parse_date(src["date_retrieved"]),
                )
            )

        breach.changelog.append(
            ChangeLog(
                changed_by="seed",
                change_type="published",
                reason="Initial load from demo fixtures.",
            )
        )

        db.add(breach)
        db.flush()  # assign breach.id before writing provenance

        for prov in b.get("provenance", []):
            db.add(
                Provenance(
                    entity="breach",
                    entity_id=breach.id,
                    field_name=prov["field_name"],
                    confidence_label=ConfidenceLabel(prov["confidence_label"]),
                    date_retrieved=_parse_date(prov.get("date_retrieved")),
                )
            )

        created += 1

    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        n = load_fixtures(db)
        print(f"Seed complete: {n} demo breach(es) created.")  # noqa: T201
    finally:
        db.close()


if __name__ == "__main__":
    main()
