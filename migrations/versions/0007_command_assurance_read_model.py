"""Command assurance read model.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assurance_results",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operational_object_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("material", sa.Boolean(), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("performer_ref", sa.String(length=255), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("source_revision", sa.String(length=255), nullable=True),
        sa.Column("homologation_state", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["operational_object_id"],
            ["operational_objects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assurance_results_organization_id"),
        "assurance_results",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assurance_results_operational_object_id"),
        "assurance_results",
        ["operational_object_id"],
        unique=False,
    )
    op.create_index(
        "ix_assurance_org_object_status",
        "assurance_results",
        ["organization_id", "operational_object_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_assurance_org_object_status", table_name="assurance_results")
    op.drop_index(
        op.f("ix_assurance_results_operational_object_id"),
        table_name="assurance_results",
    )
    op.drop_index(
        op.f("ix_assurance_results_organization_id"),
        table_name="assurance_results",
    )
    op.drop_table("assurance_results")
