"""Command observation refresh lifecycle.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "command_refresh_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("fact_class", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("source_object_type", sa.String(length=100), nullable=False),
        sa.Column("source_object_id", sa.String(length=255), nullable=False),
        sa.Column("source_reference", sa.String(length=1000), nullable=False),
        sa.Column("freshness_expectation_seconds", sa.Integer(), nullable=False),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("stale_threshold_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "failure_behavior",
            sa.String(length=40),
            nullable=False,
            server_default="preserve_last_known_degraded",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_successful_observation_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempted_observation_at", sa.DateTime(timezone=True)),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True)),
        sa.Column("last_result", sa.String(length=20)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["command_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "source_id",
            "object_key",
            name="uq_command_refresh_policy_org_source_object",
        ),
    )
    op.create_index(
        "ix_command_refresh_policies_organization_id",
        "command_refresh_policies",
        ["organization_id"],
    )
    op.create_index(
        "ix_command_refresh_policies_source_id",
        "command_refresh_policies",
        ["source_id"],
    )
    op.create_index(
        "ix_command_refresh_policies_next_eligible_at",
        "command_refresh_policies",
        ["next_eligible_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_command_refresh_policies_next_eligible_at",
        table_name="command_refresh_policies",
    )
    op.drop_index(
        "ix_command_refresh_policies_source_id",
        table_name="command_refresh_policies",
    )
    op.drop_index(
        "ix_command_refresh_policies_organization_id",
        table_name="command_refresh_policies",
    )
    op.drop_table("command_refresh_policies")
