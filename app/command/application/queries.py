from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.domain.attention import AttentionClass, AttentionSeverity
from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceType,
)
from app.command.infrastructure.models import (
    AttentionItemModel,
    CommandSourceModel,
    ObservationModel,
    OperationalObjectModel,
    ProjectionModel,
    ProjectionObservationModel,
)
from app.command.infrastructure.refresh_models import CommandRefreshPolicyModel
from app.shared.errors.exceptions import AppError


@dataclass(frozen=True)
class ProjectionView:
    object_key: str
    object_type: str
    projection_type: str
    built_at: datetime
    freshness_state: FreshnessState
    reliability_status: ObservationStatus
    trusted_current: bool
    projection_payload: dict[str, object]


@dataclass(frozen=True)
class AttentionView:
    object_key: str
    attention_class: AttentionClass
    severity: AttentionSeverity
    reason: str
    explanation: str
    freshness_state: FreshnessState


@dataclass(frozen=True)
class ProvenanceView:
    source_type: SourceType
    source_name: str
    source_reference: str
    source_revision: str | None
    observed_at: datetime
    source_updated_at: datetime | None
    retrieved_at: datetime
    observation_status: ObservationStatus
    freshness_state: FreshnessState
    current_confirmed: bool


@dataclass(frozen=True)
class ObjectDetailView:
    object_key: str
    object_type: str
    projection: ProjectionView | None
    provenance: tuple[ProvenanceView, ...]


async def _get_operational_object(
    session: AsyncSession,
    *,
    organization_id: UUID,
    object_id: UUID,
) -> OperationalObjectModel | None:
    item: OperationalObjectModel | None = await session.scalar(
        select(OperationalObjectModel).where(
            OperationalObjectModel.id == object_id,
            OperationalObjectModel.organization_id == organization_id,
        )
    )
    return item


async def _projection_view(
    session: AsyncSession,
    *,
    organization_id: UUID,
    operational_object: OperationalObjectModel,
    projection: ProjectionModel,
) -> ProjectionView:
    freshness_state = projection.freshness_state
    trusted_current = projection.trusted_current
    policy = await session.scalar(
        select(CommandRefreshPolicyModel).where(
            CommandRefreshPolicyModel.organization_id == organization_id,
            CommandRefreshPolicyModel.object_key == operational_object.object_key,
            CommandRefreshPolicyModel.enabled.is_(True),
        )
    )
    if policy is not None:
        built_at = projection.built_at
        if built_at.tzinfo is None:
            built_at = built_at.replace(tzinfo=UTC)
        stale_at = built_at + timedelta(seconds=policy.stale_threshold_seconds)
        if datetime.now(UTC) >= stale_at:
            freshness_state = FreshnessState.STALE
            trusted_current = False

    return ProjectionView(
        object_key=operational_object.object_key,
        object_type=operational_object.object_type,
        projection_type=projection.projection_type,
        built_at=projection.built_at,
        freshness_state=freshness_state,
        reliability_status=projection.reliability_status,
        trusted_current=trusted_current,
        projection_payload=projection.projection_payload,
    )


async def list_projection_views(
    session: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 20,
) -> list[ProjectionView]:
    ranked = (
        select(
            ProjectionModel.id.label("projection_id"),
            func.row_number()
            .over(
                partition_by=(
                    ProjectionModel.operational_object_id,
                    ProjectionModel.projection_type,
                ),
                order_by=(
                    ProjectionModel.built_at.desc(),
                    ProjectionModel.projection_version.desc(),
                    ProjectionModel.id.desc(),
                ),
            )
            .label("projection_rank"),
        )
        .where(ProjectionModel.organization_id == organization_id)
        .subquery()
    )
    projections = list(
        (
            await session.scalars(
                select(ProjectionModel)
                .join(ranked, ranked.c.projection_id == ProjectionModel.id)
                .where(ranked.c.projection_rank == 1)
                .order_by(ProjectionModel.built_at.desc())
                .limit(limit)
            )
        ).all()
    )
    views: list[ProjectionView] = []
    for projection in projections:
        operational_object = await _get_operational_object(
            session,
            organization_id=organization_id,
            object_id=projection.operational_object_id,
        )
        if operational_object is None:
            continue
        views.append(
            await _projection_view(
                session,
                organization_id=organization_id,
                operational_object=operational_object,
                projection=projection,
            )
        )
    return views


async def list_attention_views(
    session: AsyncSession,
    *,
    organization_id: UUID,
    attention_class: AttentionClass | None = None,
    limit: int = 20,
) -> list[AttentionView]:
    query = select(AttentionItemModel).where(
        AttentionItemModel.organization_id == organization_id
    )
    if attention_class is not None:
        query = query.where(AttentionItemModel.attention_class == attention_class)

    items = list(
        (
            await session.scalars(
                query.order_by(AttentionItemModel.created_at.desc()).limit(limit)
            )
        ).all()
    )
    views: list[AttentionView] = []
    for item in items:
        operational_object = await _get_operational_object(
            session,
            organization_id=organization_id,
            object_id=item.operational_object_id,
        )
        if operational_object is None:
            continue
        views.append(
            AttentionView(
                object_key=operational_object.object_key,
                attention_class=item.attention_class,
                severity=item.severity,
                reason=item.reason,
                explanation=item.explanation,
                freshness_state=item.freshness_state,
            )
        )
    return views


async def get_object_detail(
    session: AsyncSession,
    *,
    organization_id: UUID,
    object_key: str,
) -> ObjectDetailView:
    operational_object = await session.scalar(
        select(OperationalObjectModel).where(
            OperationalObjectModel.organization_id == organization_id,
            OperationalObjectModel.object_key == object_key,
        )
    )
    if operational_object is None:
        raise AppError(
            "Command object not found.",
            code="command_object_not_found",
            status_code=404,
        )

    projection = await session.scalar(
        select(ProjectionModel)
        .where(
            ProjectionModel.organization_id == organization_id,
            ProjectionModel.operational_object_id == operational_object.id,
        )
        .order_by(ProjectionModel.built_at.desc())
    )
    if projection is None:
        return ObjectDetailView(
            object_key=operational_object.object_key,
            object_type=operational_object.object_type,
            projection=None,
            provenance=(),
        )

    projection_view = await _projection_view(
        session,
        organization_id=organization_id,
        operational_object=operational_object,
        projection=projection,
    )
    observation_ids = list(
        (
            await session.scalars(
                select(ProjectionObservationModel.observation_id).where(
                    ProjectionObservationModel.projection_id == projection.id
                )
            )
        ).all()
    )
    provenance: list[ProvenanceView] = []
    if observation_ids:
        observations = list(
            (
                await session.scalars(
                    select(ObservationModel).where(
                        ObservationModel.organization_id == organization_id,
                        ObservationModel.id.in_(observation_ids),
                    )
                )
            ).all()
        )
        for observation in observations:
            source = await session.scalar(
                select(CommandSourceModel).where(
                    CommandSourceModel.id == observation.source_id,
                    CommandSourceModel.organization_id == organization_id,
                )
            )
            if source is None:
                continue
            provenance.append(
                ProvenanceView(
                    source_type=source.source_type,
                    source_name=source.display_name,
                    source_reference=observation.source_reference,
                    source_revision=observation.source_revision,
                    observed_at=observation.observed_at,
                    source_updated_at=observation.source_updated_at,
                    retrieved_at=observation.retrieved_at,
                    observation_status=observation.observation_status,
                    freshness_state=observation.freshness_state,
                    current_confirmed=observation.current_confirmed,
                )
            )

    return ObjectDetailView(
        object_key=operational_object.object_key,
        object_type=operational_object.object_type,
        projection=projection_view,
        provenance=tuple(provenance),
    )
