"""Command projection reliability state.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projections",
        sa.Column(
            "reliability_status",
            sa.String(length=20),
            nullable=False,
            server_default="observed",
        ),
    )
    op.add_column(
        "projections",
        sa.Column(
            "trusted_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("projections", "trusted_current")
    op.drop_column("projections", "reliability_status")
