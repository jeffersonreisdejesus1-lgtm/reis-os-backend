"""Command projection read model.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-28
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
        "operational_objects",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
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
            "object_key",
            name="uq_operational_object_org_key",
        ),
    )
    op.create_index(
        op.f("ix_operational_objects_organization_id"),
        "operational_objects",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "projections",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operational_object_id", sa.Uuid(), nullable=False),
        sa.Column("projection_type", sa.String(length=100), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("projection_version", sa.Integer(), nullable=False),
        sa.Column("freshness_state", sa.String(length=20), nullable=False),
        sa.Column("projection_payload", sa.JSON(), nullable=False),
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
        op.f("ix_projections_operational_object_id"),
        "projections",
        ["operational_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projections_organization_id"),
        "projections",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_projections_object_type_version",
        "projections",
        ["operational_object_id", "projection_type", "projection_version"],
        unique=False,
    )

    op.create_table(
        "projection_observations",
        sa.Column("projection_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["observations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["projection_id"], ["projections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("projection_id", "observation_id"),
    )


def downgrade() -> None:
    op.drop_table("projection_observations")
    op.drop_index("ix_projections_object_type_version", table_name="projections")
    op.drop_index(
        op.f("ix_projections_organization_id"), table_name="projections"
    )
    op.drop_index(
        op.f("ix_projections_operational_object_id"), table_name="projections"
    )
    op.drop_table("projections")
    op.drop_index(
        op.f("ix_operational_objects_organization_id"),
        table_name="operational_objects",
    )
    op.drop_table("operational_objects")
