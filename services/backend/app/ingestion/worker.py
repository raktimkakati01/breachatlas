"""Worker entrypoint: `python -m app.ingestion.worker` (runs the scheduler, blocking)."""

from __future__ import annotations

import logging

from app.ingestion.scheduler import build_scheduler


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("ingestion").info("ingestion worker starting")
    build_scheduler().start()


if __name__ == "__main__":
    main()
