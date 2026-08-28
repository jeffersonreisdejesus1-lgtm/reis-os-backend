from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.command.adapters.base import BaseReadAdapter, ReadAdapterRequest
from app.command.domain.attention import AttentionEngine
from app.command.domain.observation import FreshnessState, ObservationStatus
from app.command.domain.projection import (
    OperationalObjectContract,
    ProjectionBuilder,
)
from app.command.infrastructure.models import (
    AttentionItemModel,
    AttentionProjectionRefModel,
    CommandSourceModel,
    ObservationModel,
    OperationalObjectModel,
    ProjectionModel,
    ProjectionObservationModel,
)


@dataclass(frozen=True)
class IngestionReceipt:
    observation_id: UUID
    projection_id: UUID
    object_key: str
    freshness_state: FreshnessState
    reliability_status: ObservationStatus
    trusted_current: bool
    attention_ids: tuple[UUID, ...]


async def _ensure_source(
    session: AsyncSession,
    *,
    organization_id: UUID,
    request: ReadAdapterRequest,
) -> CommandSourceModel:
    source = await session.scalar(
        select(CommandSourceModel).where(
            CommandSourceModel.id == request.source.source_id,
            CommandSourceModel.organization_id == organization_id,
        )
    )
    if source is not None:
        return source

    source = CommandSourceModel(
        id=request.source.source_id,
        organization_id=organization_id,
        source_type=request.source.source_type,
        display_name=request.source.display_name,
        authority_scope=request.source.authority_scope,
        enabled=request.source.enabled,
    )
    session.add(source)
    await session.flush()
    return source


async def _ensure_operational_object(
    session: AsyncSession,
    *,
    organization_id: UUID,
    object_key: str,
    object_type: str,
) -> OperationalObjectModel:
    operational_object = await session.scalar(
        select(OperationalObjectModel).where(
            OperationalObjectModel.organization_id == organization_id,
            OperationalObjectModel.object_key == object_key,
        )
    )
    if operational_object is not None:
        return operational_object

    operational_object = OperationalObjectModel(
        organization_id=organization_id,
        object_key=object_key,
        object_type=object_type,
    )
    session.add(operational_object)
    await session.flush()
    return operational_object


async def ingest_provider_read(
    session: AsyncSession,
    *,
    organization_id: UUID,
    adapter: BaseReadAdapter,
    request: ReadAdapterRequest,
    object_key: str,
    object_type: str,
    projection_type: str = "status",
) -> IngestionReceipt:
    """Observe a provider and update only Command's internal read model."""
    await _ensure_source(session, organization_id=organization_id, request=request)
    observation = await adapter.observe(request)

    observation_model = ObservationModel(
        id=observation.observation_id,
        organization_id=organization_id,
        source_id=observation.source_id,
        source_object_type=observation.source_object_type,
        source_object_id=observation.source_object_id,
        source_reference=observation.source_reference,
        source_revision=observation.source_revision,
        observed_at=observation.observed_at,
        source_updated_at=observation.source_updated_at,
        retrieved_at=observation.retrieved_at,
        payload_normalized=observation.payload_normalized,
        observation_status=observation.observation_status,
        freshness_state=observation.freshness_state,
        freshness_reason=observation.freshness_reason,
        current_confirmed=observation.current_confirmed,
    )
    session.add(observation_model)

    operational_object = await _ensure_operational_object(
        session,
        organization_id=organization_id,
        object_key=object_key,
        object_type=object_type,
    )

    current_version = await session.scalar(
        select(func.max(ProjectionModel.projection_version)).where(
            ProjectionModel.organization_id == organization_id,
            ProjectionModel.operational_object_id == operational_object.id,
            ProjectionModel.projection_type == projection_type,
        )
    )
    projection = ProjectionBuilder().build(
        OperationalObjectContract(
            object_key=operational_object.object_key,
            object_type=operational_object.object_type,
            source_bindings=(observation.source_reference,),
        ),
        projection_type,
        [observation],
        observation.payload_normalized,
        projection_version=(current_version or 0) + 1,
    )
    projection_model = ProjectionModel(
        id=projection.projection_id,
        organization_id=organization_id,
        operational_object_id=operational_object.id,
        projection_type=projection.projection_type,
        built_at=projection.built_at,
        projection_version=projection.projection_version,
        freshness_state=projection.freshness_state,
        reliability_status=projection.reliability_status,
        trusted_current=projection.trusted_current,
        projection_payload=projection.projection_payload,
    )
    session.add(projection_model)
    await session.flush()
    session.add(
        ProjectionObservationModel(
            projection_id=projection.projection_id,
            observation_id=observation.observation_id,
        )
    )

    attention_items = AttentionEngine().evaluate(projection)
    for item in attention_items:
        session.add(
            AttentionItemModel(
                id=item.attention_id,
                organization_id=organization_id,
                operational_object_id=operational_object.id,
                rule_id=item.rule_id,
                attention_class=item.attention_class,
                reason=item.reason,
                severity=item.severity,
                freshness_state=item.freshness_state,
                explanation=item.explanation,
            )
        )
        session.add(
            AttentionProjectionRefModel(
                attention_id=item.attention_id,
                projection_id=projection.projection_id,
            )
        )

    await session.commit()
    return IngestionReceipt(
        observation_id=observation.observation_id,
        projection_id=projection.projection_id,
        object_key=projection.object_key,
        freshness_state=projection.freshness_state,
        reliability_status=projection.reliability_status,
        trusted_current=projection.trusted_current,
        attention_ids=tuple(item.attention_id for item in attention_items),
    )
