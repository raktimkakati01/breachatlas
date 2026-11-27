"""APScheduler wiring: each connector runs on its own interval inside the worker container."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingestion.connectors.edgar import SecEdgarConnector
from app.ingestion.connectors.hhs import HhsOcrConnector
from app.ingestion.connectors.ico import IcoConnector
from app.ingestion.connectors.maine import MaineAgConnector
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


def run_hhs_ocr() -> dict[str, int]:
    db = SessionLocal()
    try:
        result = ingest(db, HhsOcrConnector(), http_fetch)
        log.info("hhs_ocr ingest: %s", result)
        return result
    finally:
        db.close()


def run_maine_ag() -> dict[str, int]:
    db = SessionLocal()
    try:
        result = ingest(db, MaineAgConnector(), http_fetch)
        log.info("maine_ag ingest: %s", result)
        return result
    finally:
        db.close()


def run_uk_ico() -> dict[str, int]:
    db = SessionLocal()
    try:
        result = ingest(db, IcoConnector(), http_fetch)
        log.info("uk_ico ingest: %s", result)
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
    scheduler.add_job(
        run_hhs_ocr,
        "interval",
        hours=settings.HHS_INTERVAL_HOURS,
        id="hhs_ocr",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_maine_ag,
        "interval",
        hours=settings.MAINE_INTERVAL_HOURS,
        id="maine_ag",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_uk_ico,
        "interval",
        hours=settings.ICO_INTERVAL_HOURS,
        id="uk_ico",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
