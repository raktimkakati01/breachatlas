"""SEC EDGAR connector — 8-K filings reporting Item 1.05 (material cybersecurity incidents).

Uses the official EDGAR full-text search (EFTS) API. The required User-Agent + rate limit are
enforced by the isolated fetcher service (SEC blocks requests without a contact UA).
"""

from __future__ import annotations

import json

from app.ingestion.connectors.base import Fetch

# Full-text search for 8-K filings mentioning "Item 1.05".
EFTS_QUERY_URL = "https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K"


class SecEdgarConnector:
    name = "sec_edgar"

    def discover(self, fetch: Fetch) -> list[dict]:
        raw = fetch(EFTS_QUERY_URL)
        data = json.loads(raw)
        return data.get("hits", {}).get("hits", [])
