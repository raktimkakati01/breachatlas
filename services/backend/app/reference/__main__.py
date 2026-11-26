"""`python -m app.reference` — load all reference datasets into the database."""

from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.reference.loaders import load_all


def main() -> None:
    db = SessionLocal()
    try:
        result = load_all(db)
        print(json.dumps(result, indent=2))  # noqa: T201
    finally:
        db.close()


if __name__ == "__main__":
    main()
