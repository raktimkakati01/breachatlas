"""Tiny dependency-free slugifier for breach records."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Breach


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "breach"


def unique_breach_slug(db: Session, base: str) -> str:
    candidate = base
    n = 2
    while db.scalar(select(Breach.id).where(Breach.slug == candidate)) is not None:
        candidate = f"{base}-{n}"
        n += 1
    return candidate
