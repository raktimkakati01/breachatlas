"""Client to the isolated fetcher service. The worker fetches only through this boundary."""

from __future__ import annotations

import base64

import httpx

from app.core.config import settings


def http_fetch(url: str) -> bytes:
    resp = httpx.post(f"{settings.FETCHER_URL}/fetch", json={"url": url}, timeout=30.0)
    resp.raise_for_status()
    return base64.b64decode(resp.json()["body_base64"])
