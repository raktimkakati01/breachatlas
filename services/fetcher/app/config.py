"""Fetcher configuration from environment (kept dependency-light for the isolated image)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FetcherSettings:
    # SEC and other sources require a descriptive UA with a contact. Set a real one in prod.
    user_agent: str = os.environ.get(
        "FETCHER_USER_AGENT", "BreachAtlas-fetcher/0.1 (contact: set-FETCHER_USER_AGENT)"
    )
    timeout_seconds: float = float(os.environ.get("FETCHER_TIMEOUT_SECONDS", "10"))
    max_bytes: int = int(os.environ.get("FETCHER_MAX_BYTES", str(5 * 1024 * 1024)))  # 5 MiB
    max_redirects: int = int(os.environ.get("FETCHER_MAX_REDIRECTS", "3"))


settings = FetcherSettings()
