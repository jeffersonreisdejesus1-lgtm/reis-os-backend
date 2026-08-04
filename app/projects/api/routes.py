from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.projects.api.schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectTransitionRequest,
    ProjectUpdateRequest,
)
from app.projects.application.service import (
    create_project,
    get_project,
    list_projects,
    transition_project,
    update_project,
)
from app.shared.database.session import get_db_session
from app.shared.security.organization import CurrentOrganizationId

router = APIRouter(prefix="/projects", tags=["projects"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: ProjectCreateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> ProjectResponse:
    return ProjectResponse.model_validate(await create_project(session, organization_id=organization_id, current_user=current_user, **payload.model_dump()))


@router.get("", response_model=list[ProjectResponse])
async def list_all(organization_id: CurrentOrganizationId, session: DbSession, workspace_id: UUID | None = Query(default=None)) -> list[ProjectResponse]:
    return [ProjectResponse.model_validate(item) for item in await list_projects(session, organization_id=organization_id, workspace_id=workspace_id)]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_one(project_id: UUID, organization_id: CurrentOrganizationId, session: DbSession) -> ProjectResponse:
    return ProjectResponse.model_validate(await get_project(session, organization_id=organization_id, project_id=project_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update(project_id: UUID, payload: ProjectUpdateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> ProjectResponse:
    return ProjectResponse.model_validate(await update_project(session, organization_id=organization_id, project_id=project_id, current_user=current_user, fields_set=payload.model_fields_set, **payload.model_dump()))


@router.post("/{project_id}/transition", response_model=ProjectResponse)
async def transition(project_id: UUID, payload: ProjectTransitionRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> ProjectResponse:
    return ProjectResponse.model_validate(await transition_project(session, organization_id=organization_id, project_id=project_id, current_user=current_user, target_status=payload.target_status))
