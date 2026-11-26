"""Locate the committed reference datasets under <repo>/data/reference."""

from __future__ import annotations

import os
from pathlib import Path


def reference_dir() -> Path:
    env = os.environ.get("REFERENCE_DATA_DIR")
    if env:
        return Path(env)
    # this file: <repo>/services/backend/app/reference/paths.py  → parents[4] == <repo>
    return Path(__file__).resolve().parents[4] / "data" / "reference"


def attack_derived_path() -> Path:
    return reference_dir() / "attack" / "enterprise-attack-derived.json"


def cis_path() -> Path:
    return reference_dir() / "cis" / "cis_controls_v8.json"


def kev_path() -> Path:
    return reference_dir() / "kev" / "known_exploited_vulnerabilities.json"


def crosswalk_path() -> Path:
    return reference_dir() / "crosswalk" / "mitigation_to_control.json"
