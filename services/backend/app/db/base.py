"""Declarative base. All ORM models inherit from Base; Alembic reads Base.metadata."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
