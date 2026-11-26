"""ORM models for BreachAtlas.

Entity map:
    Breach ──< AttackStep ──< (m2m) Technique        how it happened → MITRE ATT&CK
    Breach ──< (assoc) BreachControl >── Control      which controls would have helped (CIS v8)
    Breach ──< (m2m) DataType                         what categories were exposed
    Breach ──< Source                                 citations
    Breach ──< ChangeLog                              per-breach audit trail
    Provenance                                        per-field confidence labelling (ADR-0006)
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Column as SAColumn
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    AttackPhase,
    ConfidenceLabel,
    ConfirmationStatus,
    ControlRelationship,
    ReviewStatus,
    RootCauseStatus,
    SourceType,
    UserRole,
)

# --- Plain association tables (no extra columns) ---

breach_data_types = Table(
    "breach_data_types",
    Base.metadata,
    SAColumn("breach_id", ForeignKey("breaches.id", ondelete="CASCADE"), primary_key=True),
    SAColumn("data_type_id", ForeignKey("data_types.id", ondelete="CASCADE"), primary_key=True),
)

attack_step_techniques = Table(
    "attack_step_techniques",
    Base.metadata,
    SAColumn("attack_step_id", ForeignKey("attack_steps.id", ondelete="CASCADE"), primary_key=True),
    SAColumn("technique_id", ForeignKey("techniques.id", ondelete="CASCADE"), primary_key=True),
)

# ATT&CK "mitigates" relationships: a mitigation mitigates a technique.
technique_mitigations = Table(
    "technique_mitigations",
    Base.metadata,
    SAColumn("technique_id", ForeignKey("techniques.id", ondelete="CASCADE"), primary_key=True),
    SAColumn("mitigation_id", ForeignKey("mitigations.id", ondelete="CASCADE"), primary_key=True),
)


class Breach(Base):
    __tablename__ = "breaches"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    organization: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    sector: Mapped[str] = mapped_column(String(100), index=True)
    date_disclosed: Mapped[date] = mapped_column(Date, index=True)
    date_occurred: Mapped[date | None] = mapped_column(Date, nullable=True)
    records_affected: Mapped[int | None] = mapped_column(Integer, nullable=True)

    confirmation_status: Mapped[ConfirmationStatus] = mapped_column(
        Enum(ConfirmationStatus, name="confirmation_status"),
        default=ConfirmationStatus.unconfirmed,
    )
    # Defaults to undisclosed — never guessed (ADR-0001 rule 4).
    root_cause_status: Mapped[RootCauseStatus] = mapped_column(
        Enum(RootCauseStatus, name="root_cause_status"),
        default=RootCauseStatus.undisclosed,
    )

    # Original writing only (ADR-0001 rule 2).
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_for_defenders: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_users_should_do: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review workflow state (Phase 3). Nothing is public until a human publishes it:
    # is_published only flips true on an explicit `published` transition.
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.draft,
        index=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attack_steps: Mapped[list[AttackStep]] = relationship(
        back_populates="breach",
        order_by="AttackStep.step_order",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list[Source]] = relationship(
        back_populates="breach", cascade="all, delete-orphan"
    )
    data_types: Mapped[list[DataType]] = relationship(
        secondary=breach_data_types, back_populates="breaches"
    )
    control_links: Mapped[list[BreachControl]] = relationship(
        back_populates="breach", cascade="all, delete-orphan"
    )
    changelog: Mapped[list[ChangeLog]] = relationship(
        back_populates="breach",
        order_by="ChangeLog.changed_at.desc()",
        cascade="all, delete-orphan",
    )

    @property
    def controls(self) -> list[BreachControl]:
        """Convenience accessor so response schemas can read `.controls` directly."""
        return self.control_links


class DataType(Base):
    __tablename__ = "data_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))

    breaches: Mapped[list[Breach]] = relationship(
        secondary=breach_data_types, back_populates="data_types"
    )


class AttackStep(Base):
    __tablename__ = "attack_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    breach_id: Mapped[int] = mapped_column(
        ForeignKey("breaches.id", ondelete="CASCADE"), index=True
    )
    step_order: Mapped[int] = mapped_column(Integer)
    phase: Mapped[AttackPhase] = mapped_column(Enum(AttackPhase, name="attack_phase"))
    description: Mapped[str] = mapped_column(Text)

    breach: Mapped[Breach] = relationship(back_populates="attack_steps")
    techniques: Mapped[list[Technique]] = relationship(
        secondary=attack_step_techniques, back_populates="attack_steps"
    )

    __table_args__ = (UniqueConstraint("breach_id", "step_order", name="uq_step_order_per_breach"),)


class Technique(Base):
    """MITRE ATT&CK technique. Fully loaded from ATT&CK Enterprise in Phase 2."""

    __tablename__ = "techniques"

    id: Mapped[int] = mapped_column(primary_key=True)
    technique_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. T1566
    name: Mapped[str] = mapped_column(String(255))
    # Comma-joined tactic names; a technique can belong to several tactics.
    tactic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_subtechnique: Mapped[bool] = mapped_column(Boolean, default=False)

    attack_steps: Mapped[list[AttackStep]] = relationship(
        secondary=attack_step_techniques, back_populates="techniques"
    )
    mitigations: Mapped[list[Mitigation]] = relationship(
        secondary=technique_mitigations, back_populates="techniques"
    )


class Control(Base):
    """Prevention control, mapped to CIS Controls v8 where possible (Phase 2 fills these in)."""

    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cis_control_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cis_safeguard: Mapped[str | None] = mapped_column(String(20), nullable=True)

    breach_links: Mapped[list[BreachControl]] = relationship(back_populates="control")


class BreachControl(Base):
    """Association object: links a breach to a control that would have prevented/limited it."""

    __tablename__ = "breach_controls"

    breach_id: Mapped[int] = mapped_column(
        ForeignKey("breaches.id", ondelete="CASCADE"), primary_key=True
    )
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[ControlRelationship] = mapped_column(
        Enum(ControlRelationship, name="control_relationship"),
        default=ControlRelationship.would_have_prevented,
    )

    breach: Mapped[Breach] = relationship(back_populates="control_links")
    control: Mapped[Control] = relationship(back_populates="breach_links")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    breach_id: Mapped[int] = mapped_column(
        ForeignKey("breaches.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"))
    date_retrieved: Mapped[date] = mapped_column(Date)

    breach: Mapped[Breach] = relationship(back_populates="sources")


class Provenance(Base):
    """Per-field confidence labelling (ADR-0006). `entity` + `entity_id` + `field_name`
    identify any field anywhere in the model; `confidence_label` says how much to trust it."""

    __tablename__ = "provenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "breach"
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    field_name: Mapped[str] = mapped_column(String(100))
    confidence_label: Mapped[ConfidenceLabel] = mapped_column(
        Enum(ConfidenceLabel, name="confidence_label")
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    date_retrieved: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("entity", "entity_id", "field_name", name="uq_provenance_field"),
    )


class ChangeLog(Base):
    """Per-breach changelog — when and why a record changed (feature #10)."""

    __tablename__ = "changelog"

    id: Mapped[int] = mapped_column(primary_key=True)
    breach_id: Mapped[int] = mapped_column(
        ForeignKey("breaches.id", ondelete="CASCADE"), index=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    changed_by: Mapped[str] = mapped_column(String(150))
    change_type: Mapped[str] = mapped_column(String(50))  # created | updated | published | ...
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    breach: Mapped[Breach] = relationship(back_populates="changelog")


# --- Reference data (loaded in Phase 2 from ATT&CK / CIS v8 / CISA KEV) ---


class Mitigation(Base):
    """MITRE ATT&CK mitigation / course of action (M-code)."""

    __tablename__ = "mitigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    mitigation_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. M1032
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    techniques: Mapped[list[Technique]] = relationship(
        secondary=technique_mitigations, back_populates="mitigations"
    )


class CisSafeguard(Base):
    """A CIS Controls v8 safeguard (e.g. 6.3). Reference list; titles only, no licensed text."""

    __tablename__ = "cis_safeguards"

    id: Mapped[int] = mapped_column(primary_key=True)
    safeguard_id: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # e.g. "6.3"
    control_number: Mapped[int] = mapped_column(Integer, index=True)  # 1..18
    control_title: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))


class KevEntry(Base):
    """A CISA Known Exploited Vulnerabilities (KEV) catalog entry."""

    __tablename__ = "kev_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    vendor_project: Mapped[str] = mapped_column(String(255))
    product: Mapped[str] = mapped_column(String(255))
    vulnerability_name: Mapped[str] = mapped_column(String(500))
    date_added: Mapped[date] = mapped_column(Date, index=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    known_ransomware: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- Admin: users, sessions, audit log (Phase 3) ---


class User(Base):
    """An admin-area user. Passwords are Argon2 hashes; TOTP secret is for optional MFA."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # TOTP shared secret. See docs/decisions.md: encrypt at rest in production.
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    """A server-side session. Only the SHA-256 of the opaque token is stored, never the token."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditLog(Base):
    """Immutable record of every admin action (distinct from the per-breach changelog)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)  # denormalized
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
