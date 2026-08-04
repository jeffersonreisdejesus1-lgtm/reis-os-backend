import pytest

from app.projects.domain.enums import ProjectStatus
from app.projects.domain.exceptions import InvalidProjectTransitionError
from app.projects.domain.rules import (
    PROJECT_STATUS_TRANSITIONS,
    can_transition_project,
    transition_project,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current, targets in PROJECT_STATUS_TRANSITIONS.items()
        for target in targets
    ],
)
def test_all_allowed_project_transitions_succeed(
    current: ProjectStatus,
    target: ProjectStatus,
) -> None:
    assert can_transition_project(current, target) is True
    assert transition_project(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current in ProjectStatus
        for target in ProjectStatus
        if target not in PROJECT_STATUS_TRANSITIONS[current]
    ],
)
def test_all_disallowed_project_transitions_fail(
    current: ProjectStatus,
    target: ProjectStatus,
) -> None:
    assert can_transition_project(current, target) is False

    with pytest.raises(InvalidProjectTransitionError) as error:
        transition_project(current, target)

    assert error.value.current is current
    assert error.value.target is target
