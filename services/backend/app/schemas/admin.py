"""Request/response schemas for the admin area."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ConfirmationStatus, ReviewStatus, UserRole


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, max_length=10)


class UserOut(_ORM):
    email: EmailStr
    role: UserRole
    is_active: bool
    mfa_enabled: bool


class MfaEnrollOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaVerifyIn(BaseModel):
    code: str = Field(min_length=6, max_length=10)


# --- User management (admin) ---


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: UserRole


# --- Review workflow ---


class BreachDraftCreateIn(BaseModel):
    organization: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=100)
    sector: str = Field(min_length=1, max_length=100)
    date_disclosed: date
    summary: str | None = None


class TransitionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class AdminBreachOut(_ORM):
    slug: str
    organization: str
    country: str
    sector: str
    date_disclosed: date
    records_affected: int | None = None
    confirmation_status: ConfirmationStatus
    review_status: ReviewStatus
    is_published: bool
    summary: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditLogOut(_ORM):
    actor_email: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    ip: str | None = None
    detail: str | None = None
    created_at: datetime
