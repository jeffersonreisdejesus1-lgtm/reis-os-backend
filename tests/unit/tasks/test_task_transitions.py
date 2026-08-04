import pytest

from app.tasks.domain.enums import TaskStatus
from app.tasks.domain.exceptions import InvalidTaskTransitionError
from app.tasks.domain.rules import (
    TASK_STATUS_TRANSITIONS,
    can_transition_task,
    transition_task,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current, targets in TASK_STATUS_TRANSITIONS.items()
        for target in targets
    ],
)
def test_all_allowed_task_transitions_succeed(
    current: TaskStatus,
    target: TaskStatus,
) -> None:
    assert can_transition_task(current, target) is True
    assert transition_task(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current in TaskStatus
        for target in TaskStatus
        if target not in TASK_STATUS_TRANSITIONS[current]
    ],
)
def test_all_disallowed_task_transitions_fail(
    current: TaskStatus,
    target: TaskStatus,
) -> None:
    assert can_transition_task(current, target) is False

    with pytest.raises(InvalidTaskTransitionError) as error:
        transition_task(current, target)

    assert error.value.current is current
    assert error.value.target is target
