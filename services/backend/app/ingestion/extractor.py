"""Pluggable extractor interface.

Rule-based now, behind a Protocol so an AI/LLM extractor can be dropped in later without
changing the pipeline. An extractor turns one raw source record into a normalized candidate
(or None if it can't be parsed confidently).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass
class ExtractedBreach:
    organization: str
    date_disclosed: date
    source_url: str
    source_title: str
    accession: str | None = None


class Extractor(Protocol):
    def extract(self, raw: dict) -> ExtractedBreach | None: ...


def _edgar_index_url(cik: str, accession: str) -> str:
    nodash = accession.replace("-", "")
    try:
        cik_int = int(cik)
    except (TypeError, ValueError):
        cik_int = cik
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{nodash}/{accession}-index.htm"


class RuleBasedExtractor:
    """Parses SEC EDGAR full-text search hits (EFTS JSON) into candidates."""

    def extract(self, raw: dict) -> ExtractedBreach | None:
        src = raw.get("_source", {})
        names = src.get("display_names") or []
        file_date = src.get("file_date")
        if not names or not file_date:
            return None

        # "Apple Inc. (AAPL) (CIK 0000320193)" -> "Apple Inc."
        organization = re.sub(r"\s*\(.*$", "", names[0]).strip()
        if not organization:
            return None

        accession = (raw.get("_id") or "").split(":")[0] or None
        ciks = src.get("ciks") or []
        source_url = (
            _edgar_index_url(ciks[0], accession)
            if ciks and accession
            else "https://www.sec.gov/cgi-bin/browse-edgar"
        )
        try:
            disclosed = date.fromisoformat(file_date)
        except ValueError:
            return None

        return ExtractedBreach(
            organization=organization,
            date_disclosed=disclosed,
            source_url=source_url,
            source_title=f"{src.get('form', '8-K')} (Item 1.05)",
            accession=accession,
        )
