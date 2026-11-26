"""SSRF guard tests — the core security control of the fetcher."""

from __future__ import annotations

import pytest

from app import ssrf
from app.ssrf import SSRFError, ip_is_blocked, validate_url


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata
        "100.64.0.1",  # CGNAT
        "0.0.0.0",
        "::1",
        "fc00::1",  # unique-local
        "fe80::1",  # link-local
        "::ffff:169.254.169.254",  # IPv4-mapped metadata
    ],
)
def test_blocked_ips(ip):
    assert ip_is_blocked(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "93.184.216.34", "2606:4700:4700::1111"])
def test_public_ips_allowed(ip):
    assert ip_is_blocked(ip) is False


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "file:///etc/passwd",
        "gopher://example.com",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "https://10.1.2.3/internal",
    ],
)
def test_validate_url_rejects(url):
    with pytest.raises(SSRFError):
        validate_url(url)


def test_hostname_resolving_to_private_is_rejected(monkeypatch):
    monkeypatch.setattr(
        ssrf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.0.0.5", 0))]
    )
    with pytest.raises(SSRFError):
        validate_url("http://sneaky.example.com/")


def test_hostname_resolving_to_public_is_allowed(monkeypatch):
    monkeypatch.setattr(
        ssrf.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))]
    )
    validate_url("https://example.com/")  # must not raise


def test_any_private_resolution_blocks(monkeypatch):
    # If even one resolved address is internal, reject (split-horizon / rebinding defense).
    monkeypatch.setattr(
        ssrf.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0)), (2, 1, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(SSRFError):
        validate_url("http://mixed.example.com/")
