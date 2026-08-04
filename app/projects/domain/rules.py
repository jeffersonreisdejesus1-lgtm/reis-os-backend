from app.projects.domain.enums import ProjectStatus
from app.projects.domain.exceptions import InvalidProjectTransitionError

PROJECT_STATUS_TRANSITIONS: dict[ProjectStatus, frozenset[ProjectStatus]] = {
    ProjectStatus.DRAFT: frozenset({ProjectStatus.PLANNED, ProjectStatus.CANCELLED}),
    ProjectStatus.PLANNED: frozenset({ProjectStatus.ACTIVE, ProjectStatus.CANCELLED}),
    ProjectStatus.ACTIVE: frozenset(
        {
            ProjectStatus.PAUSED,
            ProjectStatus.COMPLETED,
            ProjectStatus.CANCELLED,
        }
    ),
    ProjectStatus.PAUSED: frozenset({ProjectStatus.ACTIVE, ProjectStatus.CANCELLED}),
    ProjectStatus.COMPLETED: frozenset({ProjectStatus.ARCHIVED}),
    ProjectStatus.CANCELLED: frozenset({ProjectStatus.ARCHIVED}),
    ProjectStatus.ARCHIVED: frozenset(),
}


def can_transition_project(
    current: ProjectStatus,
    target: ProjectStatus,
) -> bool:
    return target in PROJECT_STATUS_TRANSITIONS[current]


def transition_project(
    current: ProjectStatus,
    target: ProjectStatus,
) -> ProjectStatus:
    if not can_transition_project(current, target):
        raise InvalidProjectTransitionError(current, target)
    return target
