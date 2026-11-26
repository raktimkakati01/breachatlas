"""APScheduler wiring: each connector runs on its own interval inside the worker container."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.connectors.edgar import SecEdgarConnector
from app.ingestion.fetch_client import http_fetch
from app.ingestion.pipeline import ingest

log = logging.getLogger("ingestion")


def run_sec_edgar() -> dict[str, int]:
    db = SessionLocal()
    try:
        result = ingest(db, SecEdgarConnector(), http_fetch)
        log.info("sec_edgar ingest: %s", result)
        return result
    finally:
        db.close()


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_sec_edgar,
        "interval",
        hours=settings.EDGAR_INTERVAL_HOURS,
        id="sec_edgar",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
