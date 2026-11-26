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
    RootCauseStatus,
    SourceType,
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

    # Nothing is public until a human publishes it (Phase 3 review workflow).
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
    """MITRE ATT&CK technique. Fully loaded in Phase 2; seeded minimally via fixtures now."""

    __tablename__ = "techniques"

    id: Mapped[int] = mapped_column(primary_key=True)
    technique_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. T1566
    name: Mapped[str] = mapped_column(String(255))
    tactic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    attack_steps: Mapped[list[AttackStep]] = relationship(
        secondary=attack_step_techniques, back_populates="techniques"
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
