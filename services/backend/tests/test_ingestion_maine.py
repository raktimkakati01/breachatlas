"""Maine AG connector/extractor + pipeline tests (offline, recorded CSV fixture)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.ingestion.connectors.maine import MaineAgConnector
from app.ingestion.extractor import MaineAgExtractor
from app.ingestion.pipeline import ingest
from app.models import Breach
from app.models.enums import ReviewStatus, SourceType

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "maine_ag_sample.csv"


def _fake_fetch(_url: str) -> bytes:
    return _FIXTURE.read_bytes()


def test_maine_extractor_parses_row():
    row = {
        "Entity Name": "Example Widgets LLC",
        "Reported Date": "06/12/2024",
        "Number of Maine Residents Affected": "1,240",
    }
    ext = MaineAgExtractor().extract(row)
    assert ext is not None
    assert ext.organization == "Example Widgets LLC"
    assert ext.date_disclosed == date(2024, 6, 12)
    assert ext.records_affected == 1240
    assert ext.source_type == SourceType.regulator
    assert ext.source_publisher == "Maine Attorney General"


def test_maine_extractor_skips_nameless_row():
    assert MaineAgExtractor().extract({"Entity Name": "", "Reported Date": "08/01/2024"}) is None


def test_maine_ingest_creates_candidates(fresh_session):
    result = ingest(fresh_session, MaineAgConnector(), _fake_fetch)
    assert result["discovered"] == 3
    assert result["created"] == 2
    assert result["unparsed"] == 1

    breaches = fresh_session.scalars(select(Breach)).all()
    assert {b.organization for b in breaches} == {"Example Widgets LLC", "Example Credit Union"}
    for b in breaches:
        assert b.review_status == ReviewStatus.in_review
        assert b.is_published is False
        assert b.sources[0].publisher == "Maine Attorney General"


def test_maine_ingest_deduplicates(fresh_session):
    assert ingest(fresh_session, MaineAgConnector(), _fake_fetch)["created"] == 2
    second = ingest(fresh_session, MaineAgConnector(), _fake_fetch)
    assert second["created"] == 0
    assert second["skipped"] == 2
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 2
