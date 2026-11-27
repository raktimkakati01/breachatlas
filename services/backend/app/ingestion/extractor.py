"""Pluggable extractors — one per source format, behind a common Protocol.

Each extractor turns one raw source record into a normalized `ExtractedBreach` (or None if it
can't be parsed confidently). Rule-based today; an AI/LLM extractor can implement the same
Protocol and be swapped in per connector without touching the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.models.enums import ConfirmationStatus, SourceType


@dataclass
class ExtractedBreach:
    organization: str
    date_disclosed: date
    source_url: str
    source_title: str
    source_publisher: str
    source_type: SourceType
    confirmation_status: ConfirmationStatus
    country: str = "United States"
    sector: str | None = None
    records_affected: int | None = None
    external_id: str | None = None
    # Extra provenance-bearing fields the connector is confident about, e.g.
    # {"records_affected": ConfidenceLabel.confirmed}. Pipeline merges these in.
    confident_fields: list[str] = field(default_factory=list)


class Extractor(Protocol):
    def extract(self, raw: dict) -> ExtractedBreach | None: ...


# --- SEC EDGAR ---


def _edgar_index_url(cik: str, accession: str) -> str:
    nodash = accession.replace("-", "")
    try:
        cik_int: int | str = int(cik)
    except (TypeError, ValueError):
        cik_int = cik
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{nodash}/{accession}-index.htm"


class EdgarExtractor:
    """Parses SEC EDGAR full-text search hits (EFTS JSON)."""

    def extract(self, raw: dict) -> ExtractedBreach | None:
        src = raw.get("_source", {})
        names = src.get("display_names") or []
        file_date = src.get("file_date")
        if not names or not file_date:
            return None

        organization = re.sub(r"\s*\(.*$", "", names[0]).strip()  # drop "(TICKER) (CIK ...)"
        if not organization:
            return None
        try:
            disclosed = date.fromisoformat(file_date)
        except ValueError:
            return None

        accession = (raw.get("_id") or "").split(":")[0] or None
        ciks = src.get("ciks") or []
        source_url = (
            _edgar_index_url(ciks[0], accession)
            if ciks and accession
            else "https://www.sec.gov/cgi-bin/browse-edgar"
        )
        return ExtractedBreach(
            organization=organization,
            date_disclosed=disclosed,
            source_url=source_url,
            source_title=f"{src.get('form', '8-K')} (Item 1.05)",
            source_publisher="SEC EDGAR",
            source_type=SourceType.filing,
            confirmation_status=ConfirmationStatus.confirmed,  # an official 8-K disclosure
            external_id=accession,
        )


# --- HHS OCR breach portal ---


def _parse_date(value: str) -> date | None:
    """Parse the date formats seen across sources (US m/d/Y, ISO, UK '12 September 2024')."""
    from datetime import datetime

    value = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


class HhsExtractor:
    """Parses rows from the HHS OCR breach-report CSV (500+ individual breaches)."""

    def extract(self, raw: dict) -> ExtractedBreach | None:
        name = (raw.get("Name of Covered Entity") or "").strip()
        disclosed = _parse_date(raw.get("Breach Submission Date", ""))
        if not name or disclosed is None:
            return None

        affected_raw = (raw.get("Individuals Affected") or "").replace(",", "").strip()
        records = int(affected_raw) if affected_raw.isdigit() else None

        return ExtractedBreach(
            organization=name,
            date_disclosed=disclosed,
            source_url="https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf",
            source_title="HHS OCR Breach Report (500+ individuals)",
            source_publisher="HHS OCR",
            source_type=SourceType.regulator,
            confirmation_status=ConfirmationStatus.confirmed,  # reported to the regulator
            country="United States",
            sector="Healthcare",
            records_affected=records,
            confident_fields=["records_affected"] if records is not None else [],
        )


# --- Maine Attorney General breach notifications ---


def _first_nonempty(raw: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = (raw.get(key) or "").strip()
        if value:
            return value
    return None


class MaineAgExtractor:
    """Parses rows from the Maine AG data-breach notification list (CSV).

    Column headers vary over time, so each field tries a few known aliases.
    """

    _NAME_KEYS = ["Entity Name", "Organization Name", "Business Name", "Name"]
    _DATE_KEYS = ["Reported Date", "Date Reported", "Date Received"]
    _COUNT_KEYS = [
        "Number of Maine Residents Affected",
        "Maine Residents Affected",
        "Number of Residents Affected",
        "Total number of persons affected (including residents)",
    ]

    def extract(self, raw: dict) -> ExtractedBreach | None:
        name = _first_nonempty(raw, self._NAME_KEYS)
        disclosed = _parse_date(_first_nonempty(raw, self._DATE_KEYS) or "")
        if not name or disclosed is None:
            return None

        count_raw = (_first_nonempty(raw, self._COUNT_KEYS) or "").replace(",", "")
        records = int(count_raw) if count_raw.isdigit() else None

        return ExtractedBreach(
            organization=name,
            date_disclosed=disclosed,
            source_url="https://apps.web.maine.gov/online/aeviewer/ME/40/list.html",
            source_title="Maine AG Data Breach Notification",
            source_publisher="Maine Attorney General",
            source_type=SourceType.regulator,
            confirmation_status=ConfirmationStatus.confirmed,  # filed with the state regulator
            country="United States",
            records_affected=records,
            confident_fields=["records_affected"] if records is not None else [],
        )


# --- UK ICO enforcement actions ---


class IcoExtractor:
    """Maps a parsed UK ICO enforcement-list entry into a candidate.

    The connector parses the enforcement page HTML into {organization, date, type, url} dicts;
    this extractor normalizes them. ICO actions are leads — reviewers confirm relevance, since
    not every enforcement action is a personal-data breach.
    """

    def extract(self, raw: dict) -> ExtractedBreach | None:
        organization = (raw.get("organization") or "").strip()
        disclosed = _parse_date(raw.get("date") or "")
        if not organization or disclosed is None:
            return None

        url = (raw.get("url") or "").strip()
        if url.startswith("/"):
            url = "https://ico.org.uk" + url
        if not url:
            url = "https://ico.org.uk/action-weve-taken/enforcement/"
        action_type = (raw.get("type") or "Enforcement action").strip()

        return ExtractedBreach(
            organization=organization,
            date_disclosed=disclosed,
            source_url=url,
            source_title=f"ICO: {action_type}",
            source_publisher="UK ICO",
            source_type=SourceType.regulator,
            confirmation_status=ConfirmationStatus.confirmed,  # official regulator action
            country="United Kingdom",
        )
