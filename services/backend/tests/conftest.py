"""Test harness: in-memory SQLite (no Docker/Postgres needed), seeded with demo fixtures."""

from __future__ import annotations

import os

# Must be set before app settings are imported.
os.environ["APP_ENV"] = "ci"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["API_RATE_LIMIT"] = "1000000"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.db.base import Base  # noqa: E402
from app.db.seed import load_fixtures  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app, limiter  # noqa: E402


def _new_memory_engine() -> Engine:
    # StaticPool keeps a single shared connection so the in-memory DB persists across sessions.
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


@pytest.fixture(scope="session")
def engine() -> Engine:
    """A shared, seeded in-memory database for read-path tests."""
    eng = _new_memory_engine()
    Base.metadata.create_all(eng)
    seed_session = sessionmaker(bind=eng, future=True)()
    try:
        load_fixtures(seed_session)
    finally:
        seed_session.close()
    return eng


@pytest.fixture
def session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    limiter.enabled = False  # don't rate-limit tests
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _override_get_db() -> Iterator[Session]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def fresh_session() -> Iterator[Session]:
    """An empty, isolated database for model/seed unit tests."""
    eng = _new_memory_engine()
    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng, future=True)()
    try:
        yield db
    finally:
        db.close()
        eng.dispose()
