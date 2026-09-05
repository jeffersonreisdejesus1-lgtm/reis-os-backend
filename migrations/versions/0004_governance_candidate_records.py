"""Additive candidate governance records and events.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05

Schema ownership: Alembic is the sole production physical-schema authority for
these tables. Application stores must validate this migrated schema and must not
create or alter it autonomously.

Downgrade consequence: downgrading 0004 drops governance candidate records and
events. No data-preserving rollback claim is made for this revision.
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
        "governance_candidate_records",
        sa.Column("position", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("source_refs_json", sa.JSON(), nullable=False),
        sa.Column("provenance_refs_json", sa.JSON(), nullable=False),
        sa.Column("written_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("position"),
        sa.UniqueConstraint(
            "record_type",
            "record_id",
            "schema_version",
            name="uq_governance_candidate_record_version",
        ),
    )
    op.create_index(
        "ix_governance_candidate_records_type_id",
        "governance_candidate_records",
        ["record_type", "record_id"],
        unique=False,
    )
    op.create_table(
        "governance_candidate_events",
        sa.Column("position", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_refs_json", sa.JSON(), nullable=False),
        sa.Column("provenance_refs_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("position"),
        sa.UniqueConstraint("event_id", name="uq_governance_candidate_event_id"),
    )
    op.create_index(
        "ix_governance_candidate_events_record",
        "governance_candidate_events",
        ["record_type", "record_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    # Destructive by design: 0004 has no data-preserving rollback contract.
    op.drop_index(
        "ix_governance_candidate_events_record",
        table_name="governance_candidate_events",
    )
    op.drop_table("governance_candidate_events")
    op.drop_index(
        "ix_governance_candidate_records_type_id",
        table_name="governance_candidate_records",
    )
    op.drop_table("governance_candidate_records")
