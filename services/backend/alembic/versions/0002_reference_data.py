"""reference data tables (ATT&CK mitigations, CIS safeguards, CISA KEV)

Revision ID: 0002_reference
Revises: 0001_initial
Create Date: 2026-11-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reference"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extend techniques: wider tactic (a technique can span several tactics) + subtechnique flag.
    with op.batch_alter_table("techniques") as batch:
        batch.alter_column(
            "tactic",
            existing_type=sa.String(100),
            type_=sa.String(255),
            existing_nullable=True,
        )
        batch.add_column(
            sa.Column(
                "is_subtechnique", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )

    op.create_table(
        "mitigations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mitigation_id", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
    )
    op.create_index("ix_mitigations_mitigation_id", "mitigations", ["mitigation_id"], unique=True)

    op.create_table(
        "technique_mitigations",
        sa.Column("technique_id", sa.Integer(), nullable=False),
        sa.Column("mitigation_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["technique_id"], ["techniques.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mitigation_id"], ["mitigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("technique_id", "mitigation_id"),
    )

    op.create_table(
        "cis_safeguards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("safeguard_id", sa.String(10), nullable=False),
        sa.Column("control_number", sa.Integer(), nullable=False),
        sa.Column("control_title", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
    )
    op.create_index("ix_cis_safeguards_safeguard_id", "cis_safeguards", ["safeguard_id"], unique=True)
    op.create_index("ix_cis_safeguards_control_number", "cis_safeguards", ["control_number"])

    op.create_table(
        "kev_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cve_id", sa.String(30), nullable=False),
        sa.Column("vendor_project", sa.String(255), nullable=False),
        sa.Column("product", sa.String(255), nullable=False),
        sa.Column("vulnerability_name", sa.String(500), nullable=False),
        sa.Column("date_added", sa.Date(), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("required_action", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("known_ransomware", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_kev_entries_cve_id", "kev_entries", ["cve_id"], unique=True)
    op.create_index("ix_kev_entries_date_added", "kev_entries", ["date_added"])
    op.create_index("ix_kev_entries_known_ransomware", "kev_entries", ["known_ransomware"])


def downgrade() -> None:
    op.drop_table("kev_entries")
    op.drop_table("cis_safeguards")
    op.drop_table("technique_mitigations")
    op.drop_table("mitigations")
    with op.batch_alter_table("techniques") as batch:
        batch.drop_column("is_subtechnique")
        batch.alter_column(
            "tactic",
            existing_type=sa.String(255),
            type_=sa.String(100),
            existing_nullable=True,
        )
