"""Reference-dataset loader + mapping-logic tests."""

from __future__ import annotations

import json

from sqlalchemy import func, select

from app.db.seed import load_fixtures
from app.mapping.logic import (
    controls_missing_cis_safeguard,
    mitigations_for_technique,
    suggest_controls_for_breach,
)
from app.models import Breach, CisSafeguard, Control, KevEntry, Mitigation, Technique
from app.reference.loaders import load_all, load_cis
from app.reference.paths import attack_derived_path, cis_path, kev_path


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_loaders_populate_expected_counts(ref_session):
    attack = json.loads(attack_derived_path().read_text())
    cis = json.loads(cis_path().read_text())
    kev = json.loads(kev_path().read_text())
    expected_safeguards = sum(len(c["safeguards"]) for c in cis["controls"])

    assert _count(ref_session, Technique) == len(attack["techniques"])
    assert _count(ref_session, Mitigation) == len(attack["mitigations"])
    assert _count(ref_session, CisSafeguard) == expected_safeguards == 153
    assert _count(ref_session, KevEntry) == len(kev["vulnerabilities"])


def test_loaders_are_idempotent(fresh_session):
    first = load_all(fresh_session)
    assert first["attack"]["techniques_created"] > 0
    second = load_all(fresh_session)
    assert second["attack"]["techniques_created"] == 0
    assert second["cis"]["safeguards_created"] == 0
    assert second["kev"]["kev_created"] == 0
    # updates still happen on re-run (no duplicates created)
    assert second["attack"]["techniques_updated"] == first["attack"]["techniques_created"]


def test_mitigations_for_technique(ref_session):
    mids = [m.mitigation_id for m in mitigations_for_technique(ref_session, "T1078")]
    assert "M1032" in mids  # Valid Accounts is mitigated by Multi-factor Authentication
    assert mitigations_for_technique(ref_session, "T9999") == []  # unknown technique


def test_our_controls_map_to_real_cis_safeguards(fresh_session):
    """Every Phase 1 control's cis_safeguard must exist in the CIS v8 reference."""
    load_cis(fresh_session)
    load_fixtures(fresh_session)  # creates our controls with cis_safeguard values
    assert controls_missing_cis_safeguard(fresh_session) == []


def test_bogus_safeguard_is_flagged(fresh_session):
    load_cis(fresh_session)
    fresh_session.add(Control(slug="bogus", name="Bogus", cis_safeguard="99.99"))
    fresh_session.commit()
    bad = controls_missing_cis_safeguard(fresh_session)
    assert [c.slug for c in bad] == ["bogus"]


def test_suggest_controls_for_breach(fresh_session):
    load_all(fresh_session)
    load_fixtures(fresh_session)

    breach = fresh_session.scalar(select(Breach).where(Breach.slug == "demo-retail-co-2024"))
    result = suggest_controls_for_breach(fresh_session, breach)

    # T1078 (Valid Accounts) → M1032 (MFA) and M1018/M1026 (→ least-privilege-iam)
    assert "mfa" in result["suggested_control_slugs"]
    assert "least-privilege-iam" in result["suggested_control_slugs"]
    # suggestions we actually have in our catalogue are reported as known
    assert "mfa" in result["known_controls"]
    # every evidence row carries its technique + mitigation trail
    assert all(
        {"control_slug", "via_mitigation", "via_technique"} <= set(e) for e in result["evidence"]
    )
