"""Password hashing (Argon2), opaque session tokens, and TOTP MFA helpers."""

from __future__ import annotations

import hashlib
import secrets

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


# --- Passwords ---


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:  # malformed hash, etc. — treat as auth failure, never raise
        return False


# --- Session tokens ---
# We hand the client a high-entropy opaque token and store only its SHA-256, so a
# database leak cannot be replayed as a valid session.


def new_session_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Give raw_token to the client; store token_hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- TOTP (MFA) ---


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str, issuer: str = "BreachAtlas") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    # valid_window=1 tolerates a ±30s clock skew.
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
