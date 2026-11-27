"""News-RSS connector/extractor tests: lead filtering, heuristic org, low confidence, XXE safety."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from app.ingestion.connectors.news_rss import NewsRssConnector, _parse_feed
from app.ingestion.extractor import NewsRssExtractor
from app.ingestion.pipeline import ingest
from app.models import Breach, Provenance
from app.models.enums import ConfidenceLabel, ConfirmationStatus, ReviewStatus, SourceType

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "news_sample.xml"
_FEEDS = ["https://news.example.test/feed.xml"]


def _fake_fetch(_url: str) -> bytes:
    return _FIXTURE.read_bytes()


def test_extractor_makes_lead_from_breach_headline():
    ext = NewsRssExtractor().extract(
        {
            "title": "Example Payments Ltd confirms data breach affecting 2 million customers",
            "link": "https://news.example.test/x",
            "published": "Wed, 11 Sep 2024 10:00:00 GMT",
        }
    )
    assert ext is not None
    assert ext.organization == "Example Payments Ltd"  # headline prefix before "confirms"
    assert ext.date_disclosed == date(2024, 9, 11)
    assert ext.source_type == SourceType.news
    assert ext.confirmation_status == ConfirmationStatus.unconfirmed


def test_extractor_ignores_non_breach_headline():
    assert (
        NewsRssExtractor().extract(
            {
                "title": "Conference announces 2024 keynote speakers",
                "published": "Tue, 20 Aug 2024 12:00:00 GMT",
            }
        )
        is None
    )


def test_connector_parses_rss_and_ingests_only_leads(fresh_session):
    result = ingest(fresh_session, NewsRssConnector(feeds=_FEEDS), _fake_fetch)
    # 3 items discovered, 1 non-breach dropped as unparsed → 2 leads
    assert result["discovered"] == 3
    assert result["created"] == 2
    assert result["unparsed"] == 1

    for b in fresh_session.scalars(select(Breach)).all():
        assert b.review_status == ReviewStatus.in_review
        assert b.confirmation_status == ConfirmationStatus.unconfirmed
        assert b.sources[0].source_type == SourceType.news


def test_news_org_provenance_is_analysis_not_confirmed(fresh_session):
    ingest(fresh_session, NewsRssConnector(feeds=_FEEDS), _fake_fetch)
    org_prov = fresh_session.scalars(
        select(Provenance).where(Provenance.field_name == "organization")
    ).all()
    assert org_prov
    # News org is our heuristic guess — must never be labeled Confirmed.
    assert all(p.confidence_label == ConfidenceLabel.analysis for p in org_prov)


def test_feed_parsing_rejects_xxe():
    # defusedxml must refuse entity-expansion / external-entity payloads.
    malicious = b"""<?xml version="1.0"?>
    <!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <rss version="2.0"><channel><item><title>&xxe;</title></item></channel></rss>"""
    with pytest.raises(Exception):  # noqa: B017 - defusedxml raises its own EntitiesForbidden
        _parse_feed(malicious, "evil")
