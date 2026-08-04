from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.application.service import add_audit_event
from app.shared.errors.exceptions import AppError
from app.users.infrastructure.models import UserModel
from app.workspaces.domain.enums import WorkspaceStatus, WorkspaceType
from app.workspaces.domain.rules import archive_workspace
from app.workspaces.infrastructure.models import WorkspaceModel


def snapshot(workspace: WorkspaceModel) -> dict[str, str | None]:
    return {
        "name": workspace.name,
        "slug": workspace.slug,
        "description": workspace.description,
        "type": workspace.type.value,
        "status": workspace.status.value,
    }


async def create_workspace(
    session: AsyncSession,
    *,
    organization_id: UUID,
    current_user: UserModel,
    name: str,
    slug: str,
    description: str | None,
    type: WorkspaceType,
) -> WorkspaceModel:
    workspace = WorkspaceModel(
        organization_id=organization_id,
        name=name.strip(),
        slug=slug.lower(),
        description=description,
        type=type,
        status=WorkspaceStatus.ACTIVE,
    )
    session.add(workspace)
    try:
        await session.flush()
        add_audit_event(
            session,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            action="WorkspaceCreated",
            entity_type="workspace",
            entity_id=workspace.id,
            before_data=None,
            after_data=snapshot(workspace),
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "Workspace slug is already in use.",
            code="workspace_slug_conflict",
            status_code=409,
        ) from exc
    await session.refresh(workspace)
    return workspace


async def get_workspace(
    session: AsyncSession, *, organization_id: UUID, workspace_id: UUID
) -> WorkspaceModel:
    workspace = await session.scalar(
        select(WorkspaceModel).where(
            WorkspaceModel.id == workspace_id,
            WorkspaceModel.organization_id == organization_id,
        )
    )
    if workspace is None:
        raise AppError(
            "Workspace not found.", code="workspace_not_found", status_code=404
        )
    return workspace


async def list_workspaces(
    session: AsyncSession, *, organization_id: UUID
) -> list[WorkspaceModel]:
    return list(
        (
            await session.scalars(
                select(WorkspaceModel)
                .where(WorkspaceModel.organization_id == organization_id)
                .order_by(WorkspaceModel.name)
            )
        ).all()
    )


async def update_workspace(
    session: AsyncSession,
    *,
    organization_id: UUID,
    workspace_id: UUID,
    current_user: UserModel,
    name: str | None,
    slug: str | None,
    description: str | None,
    fields_set: set[str],
    archive: bool,
) -> WorkspaceModel:
    workspace = await get_workspace(
        session, organization_id=organization_id, workspace_id=workspace_id
    )
    before = snapshot(workspace)
    action = "WorkspaceUpdated"
    if name is not None:
        workspace.name = name.strip()
    if slug is not None:
        workspace.slug = slug.lower()
    if "description" in fields_set:
        workspace.description = description
    if archive:
        workspace.status = archive_workspace(workspace.status)
        action = "WorkspaceArchived"
    try:
        await session.flush()
        add_audit_event(
            session,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            action=action,
            entity_type="workspace",
            entity_id=workspace.id,
            before_data=before,
            after_data=snapshot(workspace),
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "Workspace slug is already in use.",
            code="workspace_slug_conflict",
            status_code=409,
        ) from exc
    await session.refresh(workspace)
    return workspace
