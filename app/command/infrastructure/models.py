from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.command.domain.assurance import (
    AssuranceStatus,
    AssuranceVerdict,
    HomologationState,
)
from app.command.domain.attention import AttentionClass, AttentionSeverity
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


class OperationalObjectModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operational_objects"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "object_key",
            name="uq_operational_object_org_key",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(255))
    object_type: Mapped[str] = mapped_column(String(100))


class ProjectionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projections"
    __table_args__ = (
        Index(
            "ix_projections_object_type_version",
            "operational_object_id",
            "projection_type",
            "projection_version",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    operational_object_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_objects.id", ondelete="CASCADE"), index=True
    )
    projection_type: Mapped[str] = mapped_column(String(100))
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    projection_version: Mapped[int] = mapped_column(Integer)
    freshness_state: Mapped[FreshnessState] = mapped_column(
        Enum(
            FreshnessState,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    reliability_status: Mapped[ObservationStatus] = mapped_column(
        Enum(
            ObservationStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ObservationStatus.OBSERVED,
    )
    trusted_current: Mapped[bool] = mapped_column(Boolean, default=False)
    projection_payload: Mapped[dict[str, object]] = mapped_column(JSON)


class ProjectionObservationModel(Base):
    __tablename__ = "projection_observations"

    projection_id: Mapped[UUID] = mapped_column(
        ForeignKey("projections.id", ondelete="CASCADE"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )


class AttentionItemModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attention_items"
    __table_args__ = (
        Index(
            "ix_attention_object_severity",
            "operational_object_id",
            "severity",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    operational_object_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_objects.id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(100))
    attention_class: Mapped[AttentionClass] = mapped_column(
        Enum(
            AttentionClass,
            native_enum=False,
            length=40,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    reason: Mapped[str] = mapped_column(Text)
    severity: Mapped[AttentionSeverity] = mapped_column(
        Enum(
            AttentionSeverity,
            native_enum=False,
            length=10,
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
    explanation: Mapped[str] = mapped_column(Text)


class AttentionProjectionRefModel(Base):
    __tablename__ = "attention_projection_refs"

    attention_id: Mapped[UUID] = mapped_column(
        ForeignKey("attention_items.id", ondelete="CASCADE"), primary_key=True
    )
    projection_id: Mapped[UUID] = mapped_column(
        ForeignKey("projections.id", ondelete="RESTRICT"), primary_key=True
    )


class AssuranceResultModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assurance_results"
    __table_args__ = (
        Index(
            "ix_assurance_org_object_status",
            "organization_id",
            "operational_object_id",
            "status",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    operational_object_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_objects.id", ondelete="CASCADE"), index=True
    )
    scope: Mapped[str] = mapped_column(String(500))
    status: Mapped[AssuranceStatus] = mapped_column(
        Enum(
            AssuranceStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    material: Mapped[bool] = mapped_column(Boolean, default=True)
    verdict: Mapped[AssuranceVerdict | None] = mapped_column(
        Enum(
            AssuranceVerdict,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=True,
    )
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    performer_ref: Mapped[str] = mapped_column(String(255))
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_revision: Mapped[str | None] = mapped_column(String(255), nullable=True)
    homologation_state: Mapped[HomologationState] = mapped_column(
        Enum(
            HomologationState,
            native_enum=False,
            length=30,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=HomologationState.UNKNOWN,
    )
