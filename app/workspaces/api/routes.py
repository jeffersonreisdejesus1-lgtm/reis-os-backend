from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.shared.database.session import get_db_session
from app.shared.security.organization import CurrentOrganizationId
from app.workspaces.api.schemas import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.workspaces.application.service import (
    create_workspace,
    get_workspace,
    list_workspaces,
    update_workspace,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: WorkspaceCreateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> WorkspaceResponse:
    item = await create_workspace(session, organization_id=organization_id, current_user=current_user, **payload.model_dump())
    return WorkspaceResponse.model_validate(item)


@router.get("", response_model=list[WorkspaceResponse])
async def list_all(organization_id: CurrentOrganizationId, session: DbSession) -> list[WorkspaceResponse]:
    return [WorkspaceResponse.model_validate(item) for item in await list_workspaces(session, organization_id=organization_id)]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_one(workspace_id: UUID, organization_id: CurrentOrganizationId, session: DbSession) -> WorkspaceResponse:
    return WorkspaceResponse.model_validate(await get_workspace(session, organization_id=organization_id, workspace_id=workspace_id))


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update(workspace_id: UUID, payload: WorkspaceUpdateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> WorkspaceResponse:
    item = await update_workspace(session, organization_id=organization_id, workspace_id=workspace_id, current_user=current_user, fields_set=payload.model_fields_set, **payload.model_dump())
    return WorkspaceResponse.model_validate(item)
