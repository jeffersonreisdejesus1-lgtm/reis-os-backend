from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceType,
)
from app.shared.database.base import Base
from app.shared.database.types import TimestampMixin, UUIDPrimaryKeyMixin


class CommandSourceModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "command_sources"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_type",
            "display_name",
            name="uq_command_source_org_type_name",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(
            SourceType,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    display_name: Mapped[str] = mapped_column(String(160))
    authority_scope: Mapped[str] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ObservationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observations"
    __table_args__ = (
        Index(
            "ix_observations_source_object_time",
            "source_id",
            "source_object_id",
            "observed_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("command_sources.id", ondelete="RESTRICT"), index=True
    )
    source_object_type: Mapped[str] = mapped_column(String(100))
    source_object_id: Mapped[str] = mapped_column(String(255))
    source_reference: Mapped[str] = mapped_column(Text)
    source_revision: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_normalized: Mapped[dict[str, object]] = mapped_column(JSON)
    observation_status: Mapped[ObservationStatus] = mapped_column(
        Enum(
            ObservationStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    freshness_state: Mapped[FreshnessState] = mapped_column(
        Enum(
            FreshnessState,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    freshness_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
