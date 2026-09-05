"""Command observation contracts.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "command_sources",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("authority_scope", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
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
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "source_type",
            "display_name",
            name="uq_command_source_org_type_name",
        ),
    )
    op.create_index(
        op.f("ix_command_sources_organization_id"),
        "command_sources",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "observations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("source_object_type", sa.String(length=100), nullable=False),
        sa.Column("source_object_id", sa.String(length=255), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("source_revision", sa.String(length=255), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_normalized", sa.JSON(), nullable=False),
        sa.Column("observation_status", sa.String(length=20), nullable=False),
        sa.Column("freshness_state", sa.String(length=20), nullable=False),
        sa.Column("freshness_reason", sa.Text(), nullable=True),
        sa.Column("current_confirmed", sa.Boolean(), nullable=False),
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
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["command_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_observations_organization_id"),
        "observations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_observations_source_id"),
        "observations",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_observations_source_object_time",
        "observations",
        ["source_id", "source_object_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_observations_source_object_time", table_name="observations")
    op.drop_index(op.f("ix_observations_source_id"), table_name="observations")
    op.drop_index(
        op.f("ix_observations_organization_id"), table_name="observations"
    )
    op.drop_table("observations")
    op.drop_index(
        op.f("ix_command_sources_organization_id"), table_name="command_sources"
    )
    op.drop_table("command_sources")
