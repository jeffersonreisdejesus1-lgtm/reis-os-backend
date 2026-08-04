from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api.dependencies import CurrentUser
from app.shared.database.session import get_db_session
from app.shared.security.organization import CurrentOrganizationId
from app.tasks.api.schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskTransitionRequest,
    TaskUpdateRequest,
)
from app.tasks.application.service import (
    create_task,
    list_tasks,
    transition_task,
    update_task,
)

router = APIRouter(tags=["tasks"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create(project_id: UUID, payload: TaskCreateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> TaskResponse:
    return TaskResponse.model_validate(await create_task(session, organization_id=organization_id, project_id=project_id, current_user=current_user, **payload.model_dump()))


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_all(project_id: UUID, organization_id: CurrentOrganizationId, session: DbSession) -> list[TaskResponse]:
    return [TaskResponse.model_validate(item) for item in await list_tasks(session, organization_id=organization_id, project_id=project_id)]


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update(task_id: UUID, payload: TaskUpdateRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> TaskResponse:
    return TaskResponse.model_validate(await update_task(session, organization_id=organization_id, task_id=task_id, current_user=current_user, fields_set=payload.model_fields_set, **payload.model_dump()))


@router.post("/tasks/{task_id}/transition", response_model=TaskResponse)
async def transition(task_id: UUID, payload: TaskTransitionRequest, current_user: CurrentUser, organization_id: CurrentOrganizationId, session: DbSession) -> TaskResponse:
    return TaskResponse.model_validate(await transition_task(session, organization_id=organization_id, task_id=task_id, current_user=current_user, target_status=payload.target_status))
