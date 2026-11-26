"""SSRF guard.

The fetcher runs in its own container and must never be usable to reach internal
services or cloud metadata. This module rejects:
  * non-http(s) schemes,
  * URLs whose host (literal IP or every resolved DNS address) is private, loopback,
    link-local (incl. the 169.254.169.254 metadata endpoint), CGNAT, reserved,
    multicast or unspecified.
It is applied to the initial URL *and re-applied to every redirect hop* by the fetcher.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Carrier-grade NAT (RFC 6598) is not covered by ipaddress.is_private.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


class SSRFError(Exception):
    """Raised when a target URL fails SSRF validation."""


def ip_is_blocked(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    # IPv4-mapped IPv6 (e.g. ::ffff:169.254.169.254) must be unwrapped and re-checked.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip_is_blocked(str(ip.ipv4_mapped))
    if ip.version == 4 and ip in _CGNAT:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # includes 169.254.169.254 cloud metadata
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve(host: str) -> set[str]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFError(f"DNS resolution failed for {host!r}") from exc
    ips = {info[4][0] for info in infos}
    if not ips:
        raise SSRFError(f"{host!r} did not resolve to any address")
    return ips


def validate_url(url: str) -> None:
    """Raise SSRFError if `url` is not safe to fetch. Returns None when safe."""
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"scheme {parts.scheme!r} is not allowed")
    host = parts.hostname
    if not host:
        raise SSRFError("URL has no host")

    # Literal IP in the URL — check directly, no DNS.
    try:
        if ip_is_blocked(host):
            raise SSRFError(f"host IP {host} is in a blocked range")
        return
    except ValueError:
        pass  # not an IP literal → resolve it

    # Reject if ANY resolved address is internal (defends against split-horizon tricks).
    for ip in _resolve(host):
        if ip_is_blocked(ip):
            raise SSRFError(f"{host!r} resolves to blocked address {ip}")
