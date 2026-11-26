"""Connector interface. Each source is its own connector with its own schedule + rate limit.

A connector never fetches URLs itself: it is handed a `fetch(url) -> bytes` callable that is
backed by the isolated, SSRF-protected fetcher service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

Fetch = Callable[[str], bytes]


class Connector(Protocol):
    name: str

    def discover(self, fetch: Fetch) -> list[dict]:
        """Return raw source records (leads) to be extracted and deduplicated."""
        ...
