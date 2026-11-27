"""Maine Attorney General breach-notification connector.

Maine publishes data-breach notifications as a public list with a CSV export. Built and tested
against recorded fixtures; see docs/decisions.md for the live-access caveat.
"""

from __future__ import annotations

import csv
import io

from app.ingestion.connectors.base import Fetch
from app.ingestion.extractor import Extractor, MaineAgExtractor

MAINE_CSV_URL = "https://apps.web.maine.gov/online/aeviewer/ME/40/list.html"


class MaineAgConnector:
    name = "maine_ag"

    def __init__(self, extractor: Extractor | None = None) -> None:
        self.extractor = extractor or MaineAgExtractor()

    def discover(self, fetch: Fetch) -> list[dict]:
        text = fetch(MAINE_CSV_URL).decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))
