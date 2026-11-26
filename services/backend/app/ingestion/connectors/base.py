"""Connector interface. Each source is its own connector with its own schedule + rate limit.

A connector never fetches URLs itself: it is handed a `fetch(url) -> bytes` callable backed by
the isolated, SSRF-protected fetcher. Each connector is paired with an `extractor` that maps its
raw records to normalized candidates (swappable for an AI extractor).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from app.ingestion.extractor import Extractor

Fetch = Callable[[str], bytes]


class Connector(Protocol):
    name: str
    extractor: Extractor

    def discover(self, fetch: Fetch) -> list[dict]:
        """Return raw source records (leads) to be extracted and deduplicated."""
        ...
