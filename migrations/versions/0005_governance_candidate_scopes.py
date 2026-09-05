"""Add explicit organization scope for governance candidate projections.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05

Legacy records are intentionally left unscoped and therefore invisible through
Command. No organization is inferred during migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_candidate_scopes",
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "organization_id", "record_type", "record_id", "schema_version"
        ),
        sa.UniqueConstraint(
            "record_type", "record_id", "schema_version",
            name="uq_governance_candidate_scope_owner",
        ),
    )
    op.create_index(
        "ix_governance_candidate_scopes_organization",
        "governance_candidate_scopes",
        ["organization_id", "record_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_governance_candidate_scopes_organization",
        table_name="governance_candidate_scopes",
    )
    op.drop_table("governance_candidate_scopes")
