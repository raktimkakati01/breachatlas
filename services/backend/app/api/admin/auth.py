"""Admin authentication: login/logout, current user, and TOTP MFA enrollment."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import (
    new_totp_secret,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)
from app.crud.audit import write_audit
from app.crud.session import create_session, revoke_token
from app.crud.user import get_user_by_email
from app.db.session import get_db
from app.models import User
from app.schemas.admin import LoginIn, MfaEnrollOut, MfaVerifyIn, UserOut

router = APIRouter(prefix="/auth", tags=["admin:auth"])

_INVALID = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        raw_token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=UserOut)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(
    request: Request,
    response: Response,
    payload: LoginIn,
    db: Session = Depends(get_db),
) -> User:
    ip = get_client_ip(request)
    email = payload.email.lower()
    user = get_user_by_email(db, email)

    if (
        user is None
        or not user.is_active
        or not verify_password(user.hashed_password, payload.password)
    ):
        write_audit(db, actor=None, action="login.failure", ip=ip, detail=email)
        raise _INVALID

    if user.mfa_enabled:
        if not verify_totp(user.mfa_secret or "", payload.totp_code or ""):
            write_audit(db, actor=user, action="login.mfa_failure", ip=ip)
            raise _INVALID  # generic error — don't reveal that the password was correct

    raw = create_session(db, user, settings.SESSION_TTL_HOURS)
    user.last_login_at = datetime.now(UTC)
    write_audit(db, actor=user, action="login.success", ip=ip)
    _set_session_cookie(response, raw)
    return user


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        revoke_token(db, token)
    write_audit(db, actor=user, action="logout", ip=get_client_ip(request))
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return {"status": "logged out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/mfa/enroll", response_model=MfaEnrollOut)
def mfa_enroll(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MfaEnrollOut:
    """Generate a TOTP secret. MFA is not enforced until /mfa/verify succeeds."""
    secret = new_totp_secret()
    user.mfa_secret = secret
    user.mfa_enabled = False
    db.commit()
    return MfaEnrollOut(secret=secret, otpauth_uri=totp_provisioning_uri(secret, user.email))


@router.post("/mfa/verify", response_model=UserOut)
def mfa_verify(
    payload: MfaVerifyIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    user.mfa_enabled = True
    write_audit(db, actor=user, action="mfa.enabled", ip=get_client_ip(request))
    db.commit()
    return user
