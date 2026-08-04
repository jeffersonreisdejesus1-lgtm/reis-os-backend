from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.application.service import add_audit_event
from app.projects.domain.enums import ProjectStatus
from app.projects.domain.exceptions import InvalidProjectTransitionError
from app.projects.domain.rules import transition_project as apply_transition
from app.projects.infrastructure.models import ProjectModel
from app.shared.errors.exceptions import AppError
from app.users.infrastructure.models import UserModel
from app.workspaces.domain.enums import WorkspaceStatus
from app.workspaces.infrastructure.models import WorkspaceModel


def snapshot(item: ProjectModel) -> dict[str, str | int | None]:
    return {
        "title": item.title,
        "description": item.description,
        "status": item.status.value,
        "progress": item.progress,
        "workspace_id": str(item.workspace_id),
    }


async def _require_workspace(
    session: AsyncSession, organization_id: UUID, workspace_id: UUID
) -> None:
    exists = await session.scalar(
        select(WorkspaceModel.id).where(
            WorkspaceModel.id == workspace_id,
            WorkspaceModel.organization_id == organization_id,
            WorkspaceModel.status == WorkspaceStatus.ACTIVE,
        )
    )
    if exists is None:
        raise AppError(
            "Active workspace not found.", code="workspace_not_found", status_code=404
        )


async def create_project(
    session: AsyncSession,
    *,
    organization_id: UUID,
    current_user: UserModel,
    workspace_id: UUID,
    title: str,
    description: str | None,
) -> ProjectModel:
    await _require_workspace(session, organization_id, workspace_id)
    project = ProjectModel(
        organization_id=organization_id,
        workspace_id=workspace_id,
        title=title.strip(),
        description=description,
        status=ProjectStatus.DRAFT,
        progress=0,
        created_by=current_user.id,
    )
    session.add(project)
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="ProjectCreated",
        entity_type="project",
        entity_id=project.id,
        before_data=None,
        after_data=snapshot(project),
    )
    await session.commit()
    await session.refresh(project)
    return project


async def get_project(
    session: AsyncSession, *, organization_id: UUID, project_id: UUID
) -> ProjectModel:
    project = await session.scalar(
        select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.organization_id == organization_id,
        )
    )
    if project is None:
        raise AppError("Project not found.", code="project_not_found", status_code=404)
    return project


async def list_projects(
    session: AsyncSession, *, organization_id: UUID, workspace_id: UUID | None = None
) -> list[ProjectModel]:
    query = select(ProjectModel).where(ProjectModel.organization_id == organization_id)
    if workspace_id is not None:
        query = query.where(ProjectModel.workspace_id == workspace_id)
    return list(
        (await session.scalars(query.order_by(ProjectModel.created_at.desc()))).all()
    )


async def update_project(
    session: AsyncSession,
    *,
    organization_id: UUID,
    project_id: UUID,
    current_user: UserModel,
    title: str | None,
    description: str | None,
    progress: int | None,
    fields_set: set[str],
) -> ProjectModel:
    project = await get_project(
        session, organization_id=organization_id, project_id=project_id
    )
    before = snapshot(project)
    if title is not None:
        project.title = title.strip()
    if "description" in fields_set:
        project.description = description
    if progress is not None:
        project.progress = progress
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="ProjectUpdated",
        entity_type="project",
        entity_id=project.id,
        before_data=before,
        after_data=snapshot(project),
    )
    await session.commit()
    await session.refresh(project)
    return project


async def transition_project(
    session: AsyncSession,
    *,
    organization_id: UUID,
    project_id: UUID,
    current_user: UserModel,
    target_status: ProjectStatus,
) -> ProjectModel:
    project = await get_project(
        session, organization_id=organization_id, project_id=project_id
    )
    before = snapshot(project)
    try:
        project.status = apply_transition(project.status, target_status)
    except InvalidProjectTransitionError as exc:
        raise AppError(
            str(exc),
            code="invalid_project_transition",
            status_code=409,
        ) from exc
    if project.status == ProjectStatus.COMPLETED:
        project.progress = 100
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="ProjectTransitioned",
        entity_type="project",
        entity_id=project.id,
        before_data=before,
        after_data=snapshot(project),
    )
    await session.commit()
    await session.refresh(project)
    return project
