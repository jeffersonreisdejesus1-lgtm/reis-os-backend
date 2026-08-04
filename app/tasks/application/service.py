from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.application.service import add_audit_event
from app.memberships.domain.enums import MembershipStatus
from app.memberships.infrastructure.models import MembershipModel
from app.projects.infrastructure.models import ProjectModel
from app.shared.errors.exceptions import AppError
from app.tasks.domain.enums import TaskStatus
from app.tasks.domain.exceptions import InvalidTaskTransitionError
from app.tasks.domain.rules import transition_task as apply_transition
from app.tasks.infrastructure.models import TaskModel
from app.users.infrastructure.models import UserModel


def snapshot(item: TaskModel) -> dict[str, str | None]:
    return {
        "title": item.title,
        "description": item.description,
        "status": item.status.value,
        "assignee_id": str(item.assignee_id) if item.assignee_id else None,
        "due_date": item.due_date.isoformat() if item.due_date else None,
        "project_id": str(item.project_id),
    }


async def _require_project(
    session: AsyncSession, organization_id: UUID, project_id: UUID
) -> None:
    exists = await session.scalar(
        select(ProjectModel.id).where(
            ProjectModel.id == project_id,
            ProjectModel.organization_id == organization_id,
        )
    )
    if exists is None:
        raise AppError("Project not found.", code="project_not_found", status_code=404)


async def _validate_assignee(
    session: AsyncSession, organization_id: UUID, assignee_id: UUID | None
) -> None:
    if assignee_id is None:
        return
    membership = await session.scalar(
        select(MembershipModel.id).where(
            MembershipModel.organization_id == organization_id,
            MembershipModel.user_id == assignee_id,
            MembershipModel.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise AppError(
            "Assignee is not an active organization member.",
            code="invalid_task_assignee",
            status_code=422,
        )


async def create_task(
    session: AsyncSession,
    *,
    organization_id: UUID,
    project_id: UUID,
    current_user: UserModel,
    title: str,
    description: str | None,
    assignee_id: UUID | None,
    due_date: datetime | None,
) -> TaskModel:
    await _require_project(session, organization_id, project_id)
    await _validate_assignee(session, organization_id, assignee_id)
    task = TaskModel(
        organization_id=organization_id,
        project_id=project_id,
        title=title.strip(),
        description=description,
        status=TaskStatus.BACKLOG,
        assignee_id=assignee_id,
        due_date=due_date,
    )
    session.add(task)
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="TaskCreated",
        entity_type="task",
        entity_id=task.id,
        before_data=None,
        after_data=snapshot(task),
    )
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(
    session: AsyncSession, *, organization_id: UUID, task_id: UUID
) -> TaskModel:
    task = await session.scalar(
        select(TaskModel).where(
            TaskModel.id == task_id, TaskModel.organization_id == organization_id
        )
    )
    if task is None:
        raise AppError("Task not found.", code="task_not_found", status_code=404)
    return task


async def list_tasks(
    session: AsyncSession, *, organization_id: UUID, project_id: UUID
) -> list[TaskModel]:
    await _require_project(session, organization_id, project_id)
    return list(
        (
            await session.scalars(
                select(TaskModel)
                .where(
                    TaskModel.organization_id == organization_id,
                    TaskModel.project_id == project_id,
                )
                .order_by(TaskModel.created_at)
            )
        ).all()
    )


async def update_task(
    session: AsyncSession,
    *,
    organization_id: UUID,
    task_id: UUID,
    current_user: UserModel,
    title: str | None,
    description: str | None,
    assignee_id: UUID | None,
    due_date: datetime | None,
    fields_set: set[str],
) -> TaskModel:
    task = await get_task(session, organization_id=organization_id, task_id=task_id)
    before = snapshot(task)
    if title is not None:
        task.title = title.strip()
    if "description" in fields_set:
        task.description = description
    if "assignee_id" in fields_set:
        await _validate_assignee(session, organization_id, assignee_id)
        task.assignee_id = assignee_id
    if "due_date" in fields_set:
        task.due_date = due_date
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="TaskUpdated",
        entity_type="task",
        entity_id=task.id,
        before_data=before,
        after_data=snapshot(task),
    )
    await session.commit()
    await session.refresh(task)
    return task


async def transition_task(
    session: AsyncSession,
    *,
    organization_id: UUID,
    task_id: UUID,
    current_user: UserModel,
    target_status: TaskStatus,
) -> TaskModel:
    task = await get_task(session, organization_id=organization_id, task_id=task_id)
    before = snapshot(task)
    try:
        task.status = apply_transition(task.status, target_status)
    except InvalidTaskTransitionError as exc:
        raise AppError(
            str(exc),
            code="invalid_task_transition",
            status_code=409,
        ) from exc
    await session.flush()
    add_audit_event(
        session,
        organization_id=organization_id,
        actor_user_id=current_user.id,
        action="TaskTransitioned",
        entity_type="task",
        entity_id=task.id,
        before_data=before,
        after_data=snapshot(task),
    )
    await session.commit()
    await session.refresh(task)
    return task
