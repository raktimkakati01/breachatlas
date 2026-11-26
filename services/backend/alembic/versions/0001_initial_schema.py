"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum definitions (names match the ORM so PostgreSQL types line up).
confirmation_status = sa.Enum("confirmed", "denied", "unconfirmed", name="confirmation_status")
root_cause_status = sa.Enum("disclosed", "undisclosed", name="root_cause_status")
attack_phase = sa.Enum(
    "initial_access", "escalation_movement", "exfiltration", "impact", name="attack_phase"
)
confidence_label = sa.Enum(
    "confirmed", "reported", "analysis", "undisclosed", name="confidence_label"
)
source_type = sa.Enum("official", "regulator", "filing", "news", name="source_type")
control_relationship = sa.Enum(
    "would_have_prevented", "would_have_limited", name="control_relationship"
)

_NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "breaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False),
        sa.Column("date_disclosed", sa.Date(), nullable=False),
        sa.Column("date_occurred", sa.Date(), nullable=True),
        sa.Column("records_affected", sa.Integer(), nullable=True),
        sa.Column("confirmation_status", confirmation_status, nullable=False),
        sa.Column("root_cause_status", root_cause_status, nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("lessons_for_defenders", sa.Text(), nullable=True),
        sa.Column("what_users_should_do", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )
    op.create_index("ix_breaches_slug", "breaches", ["slug"], unique=True)
    op.create_index("ix_breaches_organization", "breaches", ["organization"])
    op.create_index("ix_breaches_country", "breaches", ["country"])
    op.create_index("ix_breaches_sector", "breaches", ["sector"])
    op.create_index("ix_breaches_date_disclosed", "breaches", ["date_disclosed"])
    op.create_index("ix_breaches_is_published", "breaches", ["is_published"])

    op.create_table(
        "data_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
    )
    op.create_index("ix_data_types_slug", "data_types", ["slug"], unique=True)

    op.create_table(
        "breach_data_types",
        sa.Column("breach_id", sa.Integer(), nullable=False),
        sa.Column("data_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["breach_id"], ["breaches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["data_type_id"], ["data_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("breach_id", "data_type_id"),
    )

    op.create_table(
        "techniques",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("technique_id", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tactic", sa.String(100), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
    )
    op.create_index("ix_techniques_technique_id", "techniques", ["technique_id"], unique=True)

    op.create_table(
        "attack_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("breach_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("phase", attack_phase, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["breach_id"], ["breaches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("breach_id", "step_order", name="uq_step_order_per_breach"),
    )
    op.create_index("ix_attack_steps_breach_id", "attack_steps", ["breach_id"])

    op.create_table(
        "attack_step_techniques",
        sa.Column("attack_step_id", sa.Integer(), nullable=False),
        sa.Column("technique_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["attack_step_id"], ["attack_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["technique_id"], ["techniques.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("attack_step_id", "technique_id"),
    )

    op.create_table(
        "controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cis_control_id", sa.String(20), nullable=True),
        sa.Column("cis_safeguard", sa.String(20), nullable=True),
    )
    op.create_index("ix_controls_slug", "controls", ["slug"], unique=True)

    op.create_table(
        "breach_controls",
        sa.Column("breach_id", sa.Integer(), nullable=False),
        sa.Column("control_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", control_relationship, nullable=False),
        sa.ForeignKeyConstraint(["breach_id"], ["breaches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["control_id"], ["controls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("breach_id", "control_id"),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("breach_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("date_retrieved", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["breach_id"], ["breaches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sources_breach_id", "sources", ["breach_id"])

    op.create_table(
        "provenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("confidence_label", confidence_label, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("date_retrieved", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("entity", "entity_id", "field_name", name="uq_provenance_field"),
    )
    op.create_index("ix_provenance_entity", "provenance", ["entity"])
    op.create_index("ix_provenance_entity_id", "provenance", ["entity_id"])

    op.create_table(
        "changelog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("breach_id", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("changed_by", sa.String(150), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("field", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["breach_id"], ["breaches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_changelog_breach_id", "changelog", ["breach_id"])


def downgrade() -> None:
    op.drop_table("changelog")
    op.drop_table("provenance")
    op.drop_table("sources")
    op.drop_table("breach_controls")
    op.drop_table("controls")
    op.drop_table("attack_step_techniques")
    op.drop_table("attack_steps")
    op.drop_table("techniques")
    op.drop_table("breach_data_types")
    op.drop_table("data_types")
    op.drop_table("breaches")

    for enum in (
        confirmation_status,
        root_cause_status,
        attack_phase,
        confidence_label,
        source_type,
        control_relationship,
    ):
        enum.drop(op.get_bind(), checkfirst=True)
