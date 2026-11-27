"""Control page, stats, and security-header tests."""

from __future__ import annotations


def test_list_controls(client):
    r = client.get("/api/v1/controls")
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()}
    assert {"mfa", "secret-scanning", "patch-management"}.issubset(slugs)


def test_control_page_lists_affected_breaches(client):
    r = client.get("/api/v1/controls/mfa")
    assert r.status_code == 200
    body = r.json()
    assert body["control"]["slug"] == "mfa"
    assert body["breach_count"] == 1
    assert body["breaches"][0]["slug"] == "demo-retail-co-2024"


def test_unknown_control_returns_404(client):
    assert client.get("/api/v1/controls/no-such-control").status_code == 404


def test_stats_reflect_published_data(client):
    body = client.get("/api/v1/stats").json()
    assert body["breaches_tracked"] == 3
    assert body["records_exposed"] == 1_285_000  # 1.2M + 85k + (undisclosed→0)
    assert body["countries"] == 2
    assert body["organizations"] == 3
    # 2 of 3 breaches have an undisclosed root cause.
    assert body["pct_undisclosed_root_cause"] == 66.7
    assert body["most_common_missing_control"] is not None


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"


def test_security_headers_present(client):
    r = client.get("/api/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert "Content-Security-Policy" in r.headers
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_write_methods_not_allowed(client):
    # Read-only API: POST to a read endpoint is rejected.
    assert client.post("/api/v1/breaches").status_code == 405
