"""Public breach API tests."""

from __future__ import annotations

from datetime import date

from app.models import Breach


def test_list_breaches_returns_published(client):
    r = client.get("/api/v1/breaches")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    slugs = {b["slug"] for b in body["items"]}
    assert "demo-retail-co-2024" in slugs


def test_list_filters_by_country_sector_year(client):
    assert client.get("/api/v1/breaches", params={"country": "United Kingdom"}).json()["total"] == 1
    assert client.get("/api/v1/breaches", params={"sector": "Healthcare"}).json()["total"] == 1
    assert client.get("/api/v1/breaches", params={"year": 2024}).json()["total"] == 1
    assert client.get("/api/v1/breaches", params={"year": 1999}).json()["total"] == 0


def test_search_by_organization(client):
    body = client.get("/api/v1/breaches", params={"q": "Acme"}).json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "acme-saas-2025"


def test_pagination(client):
    body = client.get("/api/v1/breaches", params={"limit": 2, "offset": 0}).json()
    assert len(body["items"]) == 2
    assert body["total"] == 3


def test_get_breach_detail(client):
    r = client.get("/api/v1/breaches/demo-retail-co-2024")
    assert r.status_code == 200
    body = r.json()
    assert body["organization"].startswith("Demo Retail Co")
    assert len(body["attack_steps"]) == 3
    assert body["attack_steps"][0]["techniques"][0]["technique_id"] == "T1566"
    assert any(c["control"]["slug"] == "mfa" for c in body["controls"])
    assert len(body["sources"]) == 2


def test_unknown_breach_returns_404(client):
    assert client.get("/api/v1/breaches/does-not-exist").status_code == 404


def test_unpublished_breach_is_hidden(client, session_factory):
    db = session_factory()
    try:
        db.add(
            Breach(
                slug="secret-draft",
                organization="Hidden Draft",
                country="United States",
                sector="Tech",
                date_disclosed=date(2025, 1, 1),
                is_published=False,
            )
        )
        db.commit()
        assert client.get("/api/v1/breaches/secret-draft").status_code == 404
        assert client.get("/api/v1/breaches", params={"q": "Hidden Draft"}).json()["total"] == 0
    finally:
        # clean up so other tests see the original 3 published breaches
        obj = db.query(Breach).filter_by(slug="secret-draft").one()
        db.delete(obj)
        db.commit()
        db.close()
