from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.types import TimestampMixin, UUIDPrimaryKeyMixin


class CommandRefreshPolicyModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recoverable backend-owned refresh lifecycle for one material fact class."""

    __tablename__ = "command_refresh_policies"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_id",
            "object_key",
            name="uq_command_refresh_policy_org_source_object",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("command_sources.id", ondelete="CASCADE"), index=True
    )
    fact_class: Mapped[str] = mapped_column(String(100))
    object_key: Mapped[str] = mapped_column(String(255))
    object_type: Mapped[str] = mapped_column(String(100))
    source_object_type: Mapped[str] = mapped_column(String(100))
    source_object_id: Mapped[str] = mapped_column(String(255))
    source_reference: Mapped[str] = mapped_column(String(1000))

    freshness_expectation_seconds: Mapped[int] = mapped_column(Integer)
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer)
    stale_threshold_seconds: Mapped[int] = mapped_column(Integer)
    failure_behavior: Mapped[str] = mapped_column(
        String(40), default="preserve_last_known_degraded"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_successful_observation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempted_observation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_eligible_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
