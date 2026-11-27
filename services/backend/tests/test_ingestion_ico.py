"""UK ICO connector/extractor + pipeline tests (offline, recorded HTML fixture)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.ingestion.connectors.ico import IcoConnector
from app.ingestion.extractor import IcoExtractor
from app.ingestion.pipeline import ingest
from app.models import Breach
from app.models.enums import ReviewStatus, SourceType

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ico_sample.html"


def _fake_fetch(_url: str) -> bytes:
    return _FIXTURE.read_bytes()


def test_ico_extractor_parses_entry():
    ext = IcoExtractor().extract(
        {
            "organization": "Example Media Ltd",
            "date": "12 September 2024",
            "type": "Monetary penalty",
            "url": "/action-weve-taken/enforcement/example-media-ltd/",
        }
    )
    assert ext is not None
    assert ext.organization == "Example Media Ltd"
    assert ext.date_disclosed == date(2024, 9, 12)  # UK "12 September 2024" format
    assert ext.country == "United Kingdom"
    assert ext.source_type == SourceType.regulator
    assert ext.source_url.startswith("https://ico.org.uk/")  # relative link resolved


def test_ico_extractor_skips_nameless_entry():
    assert IcoExtractor().extract({"organization": "", "date": "1 July 2024"}) is None


def test_ico_connector_parses_html_and_ingests(fresh_session):
    # Connector parses the HTML fixture; the nameless <h2> row is dropped as unparsed.
    result = ingest(fresh_session, IcoConnector(), _fake_fetch)
    assert result["discovered"] == 3
    assert result["created"] == 2
    assert result["unparsed"] == 1

    breaches = fresh_session.scalars(select(Breach)).all()
    assert {b.organization for b in breaches} == {"Example Media Ltd", "Example Council"}
    for b in breaches:
        assert b.review_status == ReviewStatus.in_review
        assert b.country == "United Kingdom"
        assert b.sources[0].publisher == "UK ICO"


def test_ico_ingest_deduplicates(fresh_session):
    assert ingest(fresh_session, IcoConnector(), _fake_fetch)["created"] == 2
    assert ingest(fresh_session, IcoConnector(), _fake_fetch)["created"] == 0
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 2
