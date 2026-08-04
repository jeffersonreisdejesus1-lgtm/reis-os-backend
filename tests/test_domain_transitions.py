import pytest

from app.projects.domain.enums import ProjectStatus
from app.projects.domain.exceptions import InvalidProjectTransitionError
from app.projects.domain.rules import transition_project
from app.shared.errors.exceptions import AppError
from app.tasks.domain.enums import TaskStatus
from app.tasks.domain.exceptions import InvalidTaskTransitionError
from app.tasks.domain.rules import transition_task
from app.workspaces.domain.enums import WorkspaceStatus
from app.workspaces.domain.rules import archive_workspace


def test_project_transition_rules() -> None:
    assert (
        transition_project(ProjectStatus.DRAFT, ProjectStatus.PLANNED)
        == ProjectStatus.PLANNED
    )
    with pytest.raises(InvalidProjectTransitionError):
        transition_project(ProjectStatus.DRAFT, ProjectStatus.COMPLETED)


def test_task_transition_rules() -> None:
    assert transition_task(TaskStatus.BACKLOG, TaskStatus.READY) == TaskStatus.READY
    with pytest.raises(InvalidTaskTransitionError):
        transition_task(TaskStatus.BACKLOG, TaskStatus.DONE)


def test_workspace_archive_rule() -> None:
    assert archive_workspace(WorkspaceStatus.ACTIVE) == WorkspaceStatus.ARCHIVED
    with pytest.raises(AppError) as error:
        archive_workspace(WorkspaceStatus.ARCHIVED)
    assert error.value.code == "invalid_workspace_transition"
