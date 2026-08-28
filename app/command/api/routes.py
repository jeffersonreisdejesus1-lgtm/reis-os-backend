from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.command.api.schemas import (
    AttentionResponse,
    CommandModeResponse,
    ObjectDetailResponse,
    ProjectionSummaryResponse,
    ProvenanceResponse,
)
from app.command.application.queries import (
    get_object_detail,
    list_attention_views,
    list_projection_views,
)
from app.command.domain.attention import AttentionClass
from app.shared.database.session import get_db_session
from app.shared.security.organization import CurrentOrganizationId

router = APIRouter(prefix="/command", tags=["command"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/mode", response_model=CommandModeResponse)
async def get_command_mode(_: CurrentUser) -> CommandModeResponse:
    """Expose the currently enforced Command capability boundary."""
    return CommandModeResponse()


@router.get("/situation", response_model=list[ProjectionSummaryResponse])
async def situation(
    organization_id: CurrentOrganizationId,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ProjectionSummaryResponse]:
    views = await list_projection_views(
        session,
        organization_id=organization_id,
        limit=limit,
    )
    return [ProjectionSummaryResponse.model_validate(item) for item in views]


@router.get("/changes", response_model=list[ProjectionSummaryResponse])
async def changes(
    organization_id: CurrentOrganizationId,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ProjectionSummaryResponse]:
    views = await list_projection_views(
        session,
        organization_id=organization_id,
        limit=limit,
    )
    return [ProjectionSummaryResponse.model_validate(item) for item in views]


@router.get("/attention", response_model=list[AttentionResponse])
async def attention(
    organization_id: CurrentOrganizationId,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AttentionResponse]:
    views = await list_attention_views(
        session,
        organization_id=organization_id,
        limit=limit,
    )
    return [AttentionResponse.model_validate(item) for item in views]


@router.get("/blockers", response_model=list[AttentionResponse])
async def blockers(
    organization_id: CurrentOrganizationId,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AttentionResponse]:
    views = await list_attention_views(
        session,
        organization_id=organization_id,
        attention_class=AttentionClass.BLOCKER,
        limit=limit,
    )
    return [AttentionResponse.model_validate(item) for item in views]


@router.get("/decisions", response_model=list[AttentionResponse])
async def decisions(
    organization_id: CurrentOrganizationId,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AttentionResponse]:
    views = await list_attention_views(
        session,
        organization_id=organization_id,
        attention_class=AttentionClass.DECISION_PENDING,
        limit=limit,
    )
    return [AttentionResponse.model_validate(item) for item in views]


@router.get("/objects/{object_key}", response_model=ObjectDetailResponse)
async def object_detail(
    object_key: str,
    organization_id: CurrentOrganizationId,
    session: DbSession,
) -> ObjectDetailResponse:
    detail = await get_object_detail(
        session,
        organization_id=organization_id,
        object_key=object_key,
    )
    projection = None
    if detail.projection is not None:
        projection = ProjectionSummaryResponse.model_validate(detail.projection)
    provenance = tuple(
        ProvenanceResponse.model_validate(item) for item in detail.provenance
    )
    return ObjectDetailResponse(
        object_key=detail.object_key,
        object_type=detail.object_type,
        projection=projection,
        provenance=provenance,
    )
