"""Model + fixture-loading tests (empty DB per test)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.seed import load_fixtures
from app.models import AttackStep, Breach, Provenance
from app.models.enums import ConfidenceLabel, RootCauseStatus


def test_root_cause_defaults_to_undisclosed(fresh_session):
    """ADR-0001 rule 4: never guess — root cause defaults to Undisclosed."""
    b = Breach(
        slug="x",
        organization="X",
        country="US",
        sector="Tech",
        date_disclosed=date(2025, 1, 1),
    )
    fresh_session.add(b)
    fresh_session.commit()
    fresh_session.refresh(b)
    assert b.root_cause_status == RootCauseStatus.undisclosed
    assert b.is_published is False  # nothing is public by default


def test_load_fixtures_creates_three_breaches(fresh_session):
    created = load_fixtures(fresh_session)
    assert created == 3
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 3


def test_load_fixtures_is_idempotent(fresh_session):
    assert load_fixtures(fresh_session) == 3
    assert load_fixtures(fresh_session) == 0  # second run creates nothing
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 3


def test_attack_steps_ordered_and_mapped_to_techniques(fresh_session):
    load_fixtures(fresh_session)
    b = fresh_session.scalar(select(Breach).where(Breach.slug == "demo-retail-co-2024"))
    orders = [s.step_order for s in b.attack_steps]
    assert orders == sorted(orders)  # relationship is ordered
    first = b.attack_steps[0]
    assert any(t.technique_id == "T1566" for t in first.techniques)


def test_control_links_carry_relationship_type(fresh_session):
    load_fixtures(fresh_session)
    b = fresh_session.scalar(select(Breach).where(Breach.slug == "demo-retail-co-2024"))
    by_slug = {link.control.slug: link.relationship_type.value for link in b.control_links}
    assert by_slug["mfa"] == "would_have_prevented"
    assert by_slug["logging-alerting"] == "would_have_limited"


def test_provenance_labels_recorded(fresh_session):
    load_fixtures(fresh_session)
    b = fresh_session.scalar(select(Breach).where(Breach.slug == "acme-saas-2025"))
    rows = fresh_session.scalars(
        select(Provenance).where(Provenance.entity == "breach", Provenance.entity_id == b.id)
    ).all()
    labels = {r.field_name: r.confidence_label for r in rows}
    # Unconfirmed breach with no stated count → records_affected labelled Undisclosed.
    assert labels["records_affected"] == ConfidenceLabel.undisclosed


def test_duplicate_step_order_rejected(fresh_session):
    b = Breach(
        slug="dup", organization="Y", country="US", sector="Tech", date_disclosed=date(2025, 1, 1)
    )
    b.attack_steps.append(AttackStep(step_order=1, phase="initial_access", description="a"))
    b.attack_steps.append(AttackStep(step_order=1, phase="impact", description="b"))
    fresh_session.add(b)
    with pytest.raises(IntegrityError):
        fresh_session.commit()
