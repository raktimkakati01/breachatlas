"""Mapping helpers built on the loaded reference data.

These power two things:
  * data-integrity checks (every control's CIS safeguard must be real), and
  * the Phase 4 extractor's *suggestions* — never auto-published, always human-reviewed.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Breach, CisSafeguard, Control, Mitigation, Technique
from app.reference.paths import crosswalk_path


@lru_cache(maxsize=1)
def _mitigation_to_control(path_str: str) -> dict[str, str]:
    data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    return dict(data["mitigation_to_control"])


def mitigation_to_control_map(path: Path | None = None) -> dict[str, str]:
    return _mitigation_to_control(str(path or crosswalk_path()))


def mitigations_for_technique(db: Session, technique_id: str) -> list[Mitigation]:
    """ATT&CK mitigations that address the given technique (e.g. 'T1078')."""
    technique = db.scalar(select(Technique).where(Technique.technique_id == technique_id))
    if technique is None:
        return []
    return sorted(technique.mitigations, key=lambda m: m.mitigation_id)


def controls_missing_cis_safeguard(db: Session) -> list[Control]:
    """Integrity check: controls whose `cis_safeguard` doesn't exist in the CIS v8 reference."""
    valid = {s.safeguard_id for s in db.scalars(select(CisSafeguard)).all()}
    bad = []
    for control in db.scalars(select(Control)).all():
        if control.cis_safeguard and control.cis_safeguard not in valid:
            bad.append(control)
    return bad


def suggest_controls_for_breach(db: Session, breach: Breach) -> dict:
    """Suggest controls for a breach: its techniques → ATT&CK mitigations → crosswalk.

    Returns the deduped suggested control slugs plus the evidence trail behind each one.
    This is advisory only; a reviewer confirms before anything is published.
    """
    crosswalk = mitigation_to_control_map()

    technique_ids = {t.technique_id for step in breach.attack_steps for t in step.techniques}

    evidence: list[dict[str, str]] = []
    suggested: set[str] = set()
    for tid in sorted(technique_ids):
        for mitigation in mitigations_for_technique(db, tid):
            control_slug = crosswalk.get(mitigation.mitigation_id)
            if control_slug is None:
                continue
            suggested.add(control_slug)
            evidence.append(
                {
                    "control_slug": control_slug,
                    "via_mitigation": mitigation.mitigation_id,
                    "mitigation_name": mitigation.name,
                    "via_technique": tid,
                }
            )

    # Note which suggested controls already exist in our catalogue.
    known = {c.slug for c in db.scalars(select(Control).where(Control.slug.in_(suggested))).all()}

    return {
        "suggested_control_slugs": sorted(suggested),
        "known_controls": sorted(known),
        "evidence": evidence,
    }
