"""safe_fetch tests: redirect re-validation and size/redirect caps (via httpx MockTransport)."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app import fetcher
from app.fetcher import safe_fetch
from app.ssrf import SSRFError

# Public IP literals avoid real DNS while MockTransport intercepts the actual request.
PUBLIC = "http://93.184.216.34/"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_simple_200(monkeypatch):
    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"hello")

    result = safe_fetch(PUBLIC, client=_client(handler))
    assert result.status_code == 200
    assert result.body == b"hello"
    assert result.redirects == 0


def test_redirect_to_internal_is_blocked():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/evil"})

    with pytest.raises(SSRFError):
        safe_fetch(PUBLIC, client=_client(handler))


def test_size_cap_enforced(monkeypatch):
    monkeypatch.setattr(
        fetcher,
        "settings",
        SimpleNamespace(max_bytes=10, max_redirects=3, timeout_seconds=5, user_agent="t"),
    )

    def handler(request):
        return httpx.Response(200, content=b"x" * 50)

    with pytest.raises(SSRFError):
        safe_fetch(PUBLIC, client=_client(handler))


def test_too_many_redirects(monkeypatch):
    monkeypatch.setattr(
        fetcher,
        "settings",
        SimpleNamespace(max_bytes=1000, max_redirects=2, timeout_seconds=5, user_agent="t"),
    )

    def handler(request):
        # Always redirect to another public IP literal → never terminates.
        return httpx.Response(302, headers={"location": "http://93.184.216.34/next"})

    with pytest.raises(SSRFError):
        safe_fetch(PUBLIC, client=_client(handler))
