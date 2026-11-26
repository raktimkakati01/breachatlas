"""Idempotent loaders that populate the reference tables from committed datasets.

Each loader upserts by natural key, so re-running updates in place without duplicates.
Run everything with:  python -m app.reference
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CisSafeguard, KevEntry, Mitigation, Technique
from app.reference.paths import attack_derived_path, cis_path, kev_path


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    # KEV dates are YYYY-MM-DD.
    return date.fromisoformat(value[:10])


def load_attack(db: Session, path: Path | None = None) -> dict[str, int]:
    data = json.loads((path or attack_derived_path()).read_text(encoding="utf-8"))

    techniques = {t.technique_id: t for t in db.scalars(select(Technique)).all()}
    t_created = t_updated = 0
    for td in data["techniques"]:
        obj = techniques.get(td["technique_id"])
        if obj is None:
            obj = Technique(technique_id=td["technique_id"])
            db.add(obj)
            techniques[obj.technique_id] = obj
            t_created += 1
        else:
            t_updated += 1
        obj.name = td["name"]
        obj.tactic = td.get("tactic")
        obj.url = td.get("url")
        obj.is_subtechnique = bool(td.get("is_subtechnique", False))

    mitigations = {m.mitigation_id: m for m in db.scalars(select(Mitigation)).all()}
    m_created = 0
    for md in data["mitigations"]:
        obj = mitigations.get(md["mitigation_id"])
        if obj is None:
            obj = Mitigation(mitigation_id=md["mitigation_id"])
            db.add(obj)
            mitigations[obj.mitigation_id] = obj
            m_created += 1
        obj.name = md["name"]
        obj.url = md.get("url")

    db.flush()

    links_added = 0
    for pair in data["technique_mitigations"]:
        t = techniques.get(pair["technique_id"])
        m = mitigations.get(pair["mitigation_id"])
        if t is not None and m is not None and m not in t.mitigations:
            t.mitigations.append(m)
            links_added += 1

    db.commit()
    return {
        "techniques_created": t_created,
        "techniques_updated": t_updated,
        "mitigations_created": m_created,
        "mappings_added": links_added,
    }


def load_cis(db: Session, path: Path | None = None) -> dict[str, int]:
    data = json.loads((path or cis_path()).read_text(encoding="utf-8"))

    existing = {s.safeguard_id: s for s in db.scalars(select(CisSafeguard)).all()}
    created = updated = 0
    for control in data["controls"]:
        for sg in control["safeguards"]:
            obj = existing.get(sg["id"])
            if obj is None:
                obj = CisSafeguard(safeguard_id=sg["id"])
                db.add(obj)
                existing[sg["id"]] = obj
                created += 1
            else:
                updated += 1
            obj.control_number = control["control"]
            obj.control_title = control["title"]
            obj.title = sg["title"]

    db.commit()
    return {"safeguards_created": created, "safeguards_updated": updated}


def load_kev(db: Session, path: Path | None = None) -> dict[str, int]:
    data = json.loads((path or kev_path()).read_text(encoding="utf-8"))

    existing = {k.cve_id: k for k in db.scalars(select(KevEntry)).all()}
    created = updated = 0
    for v in data["vulnerabilities"]:
        obj = existing.get(v["cveID"])
        if obj is None:
            obj = KevEntry(cve_id=v["cveID"])
            db.add(obj)
            existing[v["cveID"]] = obj
            created += 1
        else:
            updated += 1
        obj.vendor_project = v.get("vendorProject", "")
        obj.product = v.get("product", "")
        obj.vulnerability_name = v.get("vulnerabilityName", "")
        obj.date_added = _parse_date(v.get("dateAdded"))
        obj.short_description = v.get("shortDescription")
        obj.required_action = v.get("requiredAction")
        obj.due_date = _parse_date(v.get("dueDate"))
        obj.known_ransomware = v.get("knownRansomwareCampaignUse", "Unknown") == "Known"
        obj.notes = v.get("notes") or None

    db.commit()
    return {"kev_created": created, "kev_updated": updated}


def load_all(db: Session) -> dict[str, dict[str, int]]:
    return {
        "attack": load_attack(db),
        "cis": load_cis(db),
        "kev": load_kev(db),
    }
