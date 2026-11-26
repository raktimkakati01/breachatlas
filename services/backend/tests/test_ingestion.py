"""Ingestion pipeline tests: extractor, candidate creation, provenance, dedup, audit."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from app.ingestion.connectors.edgar import SecEdgarConnector
from app.ingestion.extractor import EdgarExtractor
from app.ingestion.pipeline import ingest
from app.models import AuditLog, Breach, Provenance
from app.models.enums import ReviewStatus

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "edgar_sample.json"


def _fake_fetch(_url: str) -> bytes:
    return _FIXTURE.read_bytes()


def test_extractor_parses_edgar_hit():
    hit = {
        "_id": "0000111111-24-000115:extc-8k.htm",
        "_source": {
            "ciks": ["0000111111"],
            "display_names": ["Example Tech Corp (EXTC) (CIK 0000111111)"],
            "file_date": "2024-09-10",
            "form": "8-K",
        },
    }
    ext = EdgarExtractor().extract(hit)
    assert ext is not None
    assert ext.organization == "Example Tech Corp"
    assert ext.date_disclosed == date(2024, 9, 10)
    assert ext.external_id == "0000111111-24-000115"
    assert "edgar/data" in ext.source_url


def test_extractor_returns_none_without_names():
    assert EdgarExtractor().extract({"_id": "x", "_source": {"file_date": "2024-10-02"}}) is None


def test_ingest_creates_review_candidates(fresh_session):
    result = ingest(fresh_session, SecEdgarConnector(), _fake_fetch)
    assert result == {"discovered": 3, "created": 2, "skipped": 0, "unparsed": 1}

    breaches = fresh_session.scalars(select(Breach)).all()
    assert len(breaches) == 2
    for b in breaches:
        assert b.review_status == ReviewStatus.in_review  # queued, never auto-published
        assert b.is_published is False
        assert len(b.sources) == 1
        assert b.sources[0].publisher == "SEC EDGAR"


def test_ingest_records_provenance_and_audit(fresh_session):
    ingest(fresh_session, SecEdgarConnector(), _fake_fetch)

    prov_fields = {
        p.field_name
        for p in fresh_session.scalars(
            select(Provenance).where(Provenance.entity == "breach")
        ).all()
    }
    assert {"organization", "date_disclosed", "country", "root_cause_status"} <= prov_fields

    ingested = fresh_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "breach.ingested")
    )
    assert ingested == 2


def test_ingest_is_deduplicated(fresh_session):
    first = ingest(fresh_session, SecEdgarConnector(), _fake_fetch)
    assert first["created"] == 2
    second = ingest(fresh_session, SecEdgarConnector(), _fake_fetch)
    assert second["created"] == 0
    assert second["skipped"] == 2  # same org + date → deduplicated
    assert fresh_session.scalar(select(func.count()).select_from(Breach)) == 2
