"""Server-side session CRUD. Only token hashes are stored."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token, new_session_token
from app.models import User, UserSession


def _aware(dt: datetime) -> datetime:
    """Treat DB-returned naive datetimes (SQLite) as UTC for safe comparison."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def create_session(db: Session, user: User, ttl_hours: int) -> str:
    """Create a session and return the RAW token (store only its hash)."""
    raw, token_hash = new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
    )
    db.commit()
    return raw


def user_for_token(db: Session, raw_token: str) -> User | None:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
    if session is None or session.revoked_at is not None:
        return None
    if _aware(session.expires_at) <= datetime.now(UTC):
        return None
    user = session.user
    return user if user.is_active else None


def revoke_token(db: Session, raw_token: str) -> None:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()
