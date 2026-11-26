"""HHS OCR breach-portal connector — US healthcare breaches affecting 500+ individuals.

The portal publishes the breach list as CSV (public-domain U.S. Government data). The live export
is JSF-driven; see docs/decisions.md. Built and tested against recorded fixtures.
"""

from __future__ import annotations

import csv
import io

from app.ingestion.connectors.base import Fetch
from app.ingestion.extractor import Extractor, HhsExtractor

# Portal/export endpoint. Live export requires the portal's JSF CSV download (see decisions).
HHS_CSV_URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf"


class HhsOcrConnector:
    name = "hhs_ocr"

    def __init__(self, extractor: Extractor | None = None) -> None:
        self.extractor = extractor or HhsExtractor()

    def discover(self, fetch: Fetch) -> list[dict]:
        text = fetch(HHS_CSV_URL).decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))
