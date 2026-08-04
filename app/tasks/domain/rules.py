from app.tasks.domain.enums import TaskStatus
from app.tasks.domain.exceptions import InvalidTaskTransitionError

TASK_STATUS_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.BACKLOG: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.BLOCKED, TaskStatus.REVIEW, TaskStatus.CANCELLED}
    ),
    TaskStatus.BLOCKED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.REVIEW: frozenset(
        {TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED}
    ),
    TaskStatus.DONE: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def can_transition_task(
    current: TaskStatus,
    target: TaskStatus,
) -> bool:
    return target in TASK_STATUS_TRANSITIONS[current]


def transition_task(
    current: TaskStatus,
    target: TaskStatus,
) -> TaskStatus:
    if not can_transition_task(current, target):
        raise InvalidTaskTransitionError(current, target)
    return target
