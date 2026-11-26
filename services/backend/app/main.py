"""BreachAtlas backend — read-only public API.

Security posture (Phase 1 baseline):
  * Read-only API, rate limited per client IP (slowapi).
  * Secure response headers on every response.
  * Parameterized queries only (SQLAlchemy ORM) — no string-built SQL.
  * Strict input validation via Pydantic / FastAPI query constraints.
The admin/write surface and its auth arrive in Phase 3.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.config import settings

# Paths that must keep inline scripts (Swagger UI / ReDoc) — excluded from the strict CSP.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.API_RATE_LIMIT}/minute"],
)

app = FastAPI(
    title="BreachAtlas API",
    version="0.1.0",
    description="Read-only public API over publicly reported data breaches and their mappings.",
    summary="How breaches happened and which controls would have stopped them.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],  # read-only API
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    # A locked-down CSP for API responses; docs UIs need inline scripts so are exempted.
    if not request.url.path.startswith(_DOCS_PATHS):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "breachatlas-api", "docs": "/docs", "api": "/api/v1"}
