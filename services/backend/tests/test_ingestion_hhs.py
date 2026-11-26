"""HHS OCR connector/extractor + pipeline tests (offline, recorded CSV fixture)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.ingestion.connectors.hhs import HhsOcrConnector
from app.ingestion.extractor import HhsExtractor
from app.ingestion.pipeline import ingest
from app.models import Breach, Provenance
from app.models.enums import ConfidenceLabel, ReviewStatus, SourceType

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hhs_sample.csv"


def _fake_fetch(_url: str) -> bytes:
    return _FIXTURE.read_bytes()


def test_hhs_extractor_parses_row():
    row = {
        "Name of Covered Entity": "Example Regional Hospital",
        "Individuals Affected": "52,000",
        "Breach Submission Date": "09/15/2024",
    }
    ext = HhsExtractor().extract(row)
    assert ext is not None
    assert ext.organization == "Example Regional Hospital"
    assert ext.date_disclosed == date(2024, 9, 15)
    assert ext.records_affected == 52000
    assert ext.sector == "Healthcare"
    assert ext.source_type == SourceType.regulator


def test_hhs_extractor_skips_nameless_row():
    assert (
        HhsExtractor().extract(
            {"Name of Covered Entity": "", "Breach Submission Date": "10/01/2024"}
        )
        is None
    )


def test_hhs_ingest_creates_candidates(fresh_session):
    result = ingest(fresh_session, HhsOcrConnector(), _fake_fetch)
    assert result["discovered"] == 3
    assert result["created"] == 2
    assert result["unparsed"] == 1

    breaches = fresh_session.scalars(select(Breach)).all()
    assert {b.organization for b in breaches} == {
        "Example Regional Hospital",
        "Example Health Plan Inc.",
    }
    for b in breaches:
        assert b.review_status == ReviewStatus.in_review
        assert b.is_published is False
        assert b.sector == "Healthcare"
        assert b.sources[0].publisher == "HHS OCR"
        assert b.records_affected is not None


def test_hhs_records_affected_is_confirmed_provenance(fresh_session):
    ingest(fresh_session, HhsOcrConnector(), _fake_fetch)
    rows = fresh_session.scalars(
        select(Provenance).where(Provenance.field_name == "records_affected")
    ).all()
    assert rows
    assert all(r.confidence_label == ConfidenceLabel.confirmed for r in rows)


def test_hhs_ingest_deduplicates(fresh_session):
    assert ingest(fresh_session, HhsOcrConnector(), _fake_fetch)["created"] == 2
    second = ingest(fresh_session, HhsOcrConnector(), _fake_fetch)
    assert second["created"] == 0
    assert second["skipped"] == 2
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 2
