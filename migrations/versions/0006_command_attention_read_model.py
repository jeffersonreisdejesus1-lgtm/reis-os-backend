"""Command attention read model.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attention_items",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operational_object_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("attention_class", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("freshness_state", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
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
        op.f("ix_attention_items_organization_id"),
        "attention_items",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attention_items_operational_object_id"),
        "attention_items",
        ["operational_object_id"],
        unique=False,
    )
    op.create_index(
        "ix_attention_object_severity",
        "attention_items",
        ["operational_object_id", "severity"],
        unique=False,
    )

    op.create_table(
        "attention_projection_refs",
        sa.Column("attention_id", sa.Uuid(), nullable=False),
        sa.Column("projection_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attention_id"], ["attention_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["projection_id"], ["projections.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("attention_id", "projection_id"),
    )


def downgrade() -> None:
    op.drop_table("attention_projection_refs")
    op.drop_index("ix_attention_object_severity", table_name="attention_items")
    op.drop_index(
        op.f("ix_attention_items_operational_object_id"),
        table_name="attention_items",
    )
    op.drop_index(
        op.f("ix_attention_items_organization_id"),
        table_name="attention_items",
    )
    op.drop_table("attention_items")
