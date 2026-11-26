#!/usr/bin/env python3
"""Build compact, committed reference datasets from large upstream source files.

Run with an isolated interpreter (the inputs are downloaded data):
    python3 -I scripts/build_reference.py <attack_stix.json> <out_dir>

Produces <out_dir>/enterprise-attack-derived.json containing only the objects BreachAtlas
loads (techniques, mitigations, and their 'mitigates' mappings) — a few MB instead of ~55 MB.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path


def _mitre_ref(obj: dict) -> dict | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            return ref
    return None


def _tactics(obj: dict) -> list[str]:
    out = []
    for ph in obj.get("kill_chain_phases", []):
        if ph.get("kill_chain_name") == "mitre-attack":
            out.append(ph["phase_name"].replace("-", " ").title())
    return out


def _is_live(obj: dict) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def build(attack_path: Path, out_dir: Path) -> dict:
    raw = attack_path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    bundle = json.loads(raw)
    objects = bundle["objects"]

    techniques: dict[str, dict] = {}
    mitigations: dict[str, dict] = {}
    stix_to_attack: dict[str, str] = {}

    for obj in objects:
        otype = obj.get("type")
        if otype == "attack-pattern" and _is_live(obj):
            ref = _mitre_ref(obj)
            if not ref:
                continue
            tid = ref["external_id"]
            stix_to_attack[obj["id"]] = tid
            techniques[tid] = {
                "technique_id": tid,
                "name": obj["name"],
                "tactic": ", ".join(_tactics(obj)) or None,
                "url": ref.get("url"),
                "is_subtechnique": bool(obj.get("x_mitre_is_subtechnique", False)),
            }
        elif otype == "course-of-action" and _is_live(obj):
            ref = _mitre_ref(obj)
            if not ref or not ref["external_id"].startswith("M"):
                continue
            mid = ref["external_id"]
            stix_to_attack[obj["id"]] = mid
            mitigations[mid] = {
                "mitigation_id": mid,
                "name": obj["name"],
                "url": ref.get("url"),
            }

    pairs: set[tuple[str, str]] = set()
    for obj in objects:
        if obj.get("type") != "relationship" or obj.get("relationship_type") != "mitigates":
            continue
        src = stix_to_attack.get(obj.get("source_ref", ""))  # mitigation
        tgt = stix_to_attack.get(obj.get("target_ref", ""))  # technique
        if src and tgt and src in mitigations and tgt in techniques:
            pairs.add((tgt, src))

    derived = {
        "_meta": {
            "source": "MITRE ATT&CK Enterprise (STIX)",
            "source_repo": "https://github.com/mitre-attack/attack-stix-data",
            "attack_version": "20.1",
            "source_file": attack_path.name,
            "source_sha256": sha256,
            "retrieved": date.today().isoformat(),
            "license": "ATT&CK Terms of Use — https://attack.mitre.org/resources/legal-and-branding/terms-of-use/",
            "note": "Derived subset: techniques, mitigations, and mitigates mappings only.",
        },
        "techniques": sorted(techniques.values(), key=lambda t: t["technique_id"]),
        "mitigations": sorted(mitigations.values(), key=lambda m: m["mitigation_id"]),
        "technique_mitigations": [
            {"technique_id": t, "mitigation_id": m} for t, m in sorted(pairs)
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "enterprise-attack-derived.json"
    out_path.write_text(json.dumps(derived, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "techniques": len(derived["techniques"]),
        "mitigations": len(derived["mitigations"]),
        "mappings": len(derived["technique_mitigations"]),
        "out": str(out_path),
        "bytes": out_path.stat().st_size,
    }


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    stats = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
