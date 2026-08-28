from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.domain.attention import AttentionClass, AttentionSeverity
from app.command.domain.observation import FreshnessState, SourceType
from app.command.infrastructure.models import (
    AttentionItemModel,
    CommandSourceModel,
    ObservationModel,
    OperationalObjectModel,
    ProjectionModel,
    ProjectionObservationModel,
)
from app.shared.errors.exceptions import AppError


@dataclass(frozen=True)
class ProjectionView:
    object_key: str
    object_type: str
    projection_type: str
    built_at: datetime
    freshness_state: FreshnessState
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
    freshness_state: FreshnessState


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


async def list_projection_views(
    session: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 20,
) -> list[ProjectionView]:
    projections = list(
        (
            await session.scalars(
                select(ProjectionModel)
                .where(ProjectionModel.organization_id == organization_id)
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
            ProjectionView(
                object_key=operational_object.object_key,
                object_type=operational_object.object_type,
                projection_type=projection.projection_type,
                built_at=projection.built_at,
                freshness_state=projection.freshness_state,
                projection_payload=projection.projection_payload,
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

    projection_view = ProjectionView(
        object_key=operational_object.object_key,
        object_type=operational_object.object_type,
        projection_type=projection.projection_type,
        built_at=projection.built_at,
        freshness_state=projection.freshness_state,
        projection_payload=projection.projection_payload,
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
                    freshness_state=observation.freshness_state,
                )
            )

    return ObjectDetailView(
        object_key=operational_object.object_key,
        object_type=operational_object.object_type,
        projection=projection_view,
        provenance=tuple(provenance),
    )
