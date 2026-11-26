"""Minimal internal HTTP API for the fetcher. Only the worker should reach this service."""

from __future__ import annotations

import base64

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.fetcher import safe_fetch
from app.ssrf import SSRFError

app = FastAPI(title="BreachAtlas Fetcher", version="0.1.0")


class FetchIn(BaseModel):
    url: str = Field(max_length=2000)


class FetchOut(BaseModel):
    final_url: str
    status_code: int
    content_type: str | None
    redirects: int
    elapsed_ms: int
    body_base64: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fetch", response_model=FetchOut)
def fetch(payload: FetchIn) -> FetchOut:
    try:
        result = safe_fetch(payload.url)
    except SSRFError as exc:
        # 422: the request was well-formed but the target is not permitted.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return FetchOut(
        final_url=result.final_url,
        status_code=result.status_code,
        content_type=result.content_type,
        redirects=result.redirects,
        elapsed_ms=result.elapsed_ms,
        body_base64=base64.b64encode(result.body).decode("ascii"),
    )
