"""Shared rate limiter (separate module so routers can import it without circular deps)."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.API_RATE_LIMIT}/minute"],
)
