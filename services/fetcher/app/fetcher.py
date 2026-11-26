"""Safe fetch: SSRF validation on every hop, manual redirects, and size/time/redirect caps."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings
from app.ssrf import SSRFError, validate_url


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    content_type: str | None
    body: bytes
    elapsed_ms: int
    redirects: int


def safe_fetch(url: str, *, client: httpx.Client | None = None) -> FetchResult:
    """Fetch `url` with SSRF protection. Raises SSRFError on any unsafe hop or cap breach."""
    start = time.monotonic()
    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=False,
        timeout=settings.timeout_seconds,
        headers={"User-Agent": settings.user_agent},
    )
    try:
        current = url
        for hop in range(settings.max_redirects + 1):
            validate_url(current)  # re-validate every hop (defends against redirect-to-internal)
            with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise SSRFError("redirect without a Location header")
                    current = str(resp.url.join(location))
                    continue

                total = 0
                chunks: list[bytes] = []
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > settings.max_bytes:
                        raise SSRFError(f"response exceeded {settings.max_bytes} bytes")
                    chunks.append(chunk)

                return FetchResult(
                    url=url,
                    final_url=str(resp.url),
                    status_code=resp.status_code,
                    content_type=resp.headers.get("content-type"),
                    body=b"".join(chunks),
                    elapsed_ms=int((time.monotonic() - start) * 1000),
                    redirects=hop,
                )
        raise SSRFError(f"exceeded {settings.max_redirects} redirects")
    finally:
        if owns_client:
            client.close()
