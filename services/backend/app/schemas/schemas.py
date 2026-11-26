"""Pydantic v2 response schemas for the read-only public API.

Request validation for writes arrives with the admin API in Phase 3. For now these are
output shapes; `from_attributes=True` lets them read straight off ORM objects.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    AttackPhase,
    ConfidenceLabel,
    ConfirmationStatus,
    ControlRelationship,
    RootCauseStatus,
    SourceType,
)


class _ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TechniqueOut(_ORMModel):
    technique_id: str
    name: str
    tactic: str | None = None
    url: str | None = None


class DataTypeOut(_ORMModel):
    slug: str
    name: str


class ControlOut(_ORMModel):
    slug: str
    name: str
    description: str | None = None
    cis_control_id: str | None = None
    cis_safeguard: str | None = None


class SourceOut(_ORMModel):
    url: str
    title: str | None = None
    publisher: str | None = None
    source_type: SourceType
    date_retrieved: date


class AttackStepOut(_ORMModel):
    step_order: int
    phase: AttackPhase
    description: str
    techniques: list[TechniqueOut] = []


class BreachControlOut(_ORMModel):
    """A control linked to a breach, with how it relates (prevented vs. limited)."""

    relationship_type: ControlRelationship
    control: ControlOut


class ProvenanceOut(_ORMModel):
    field_name: str
    confidence_label: ConfidenceLabel
    date_retrieved: date | None = None


class BreachSummaryOut(_ORMModel):
    """Compact shape for list/search results."""

    slug: str
    organization: str
    country: str
    sector: str
    date_disclosed: date
    records_affected: int | None = None
    confirmation_status: ConfirmationStatus
    root_cause_status: RootCauseStatus


class BreachDetailOut(_ORMModel):
    slug: str
    organization: str
    country: str
    sector: str
    date_disclosed: date
    date_occurred: date | None = None
    records_affected: int | None = None
    confirmation_status: ConfirmationStatus
    root_cause_status: RootCauseStatus
    summary: str | None = None
    lessons_for_defenders: str | None = None
    what_users_should_do: str | None = None
    created_at: datetime
    updated_at: datetime
    data_types: list[DataTypeOut] = []
    attack_steps: list[AttackStepOut] = []
    sources: list[SourceOut] = []
    controls: list[BreachControlOut] = []


class PaginatedBreaches(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[BreachSummaryOut]


class ControlPageOut(BaseModel):
    """A control plus every published breach it was a factor in (e.g. 'MFA')."""

    control: ControlOut
    breach_count: int
    breaches: list[BreachSummaryOut]


class StatsOut(BaseModel):
    breaches_tracked: int
    records_exposed: int
    countries: int
    organizations: int
    most_common_missing_control: str | None = None
    pct_undisclosed_root_cause: float


class HealthOut(BaseModel):
    status: str
    env: str
