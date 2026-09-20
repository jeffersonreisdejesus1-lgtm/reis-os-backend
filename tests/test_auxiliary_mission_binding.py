import pytest

from app.ocs_instances.mission_binding import (
    AuxiliaryMissionBindingError,
    AuxiliaryMissionRequest,
    bind_auxiliary_mission,
)


def request(**changes: str) -> AuxiliaryMissionRequest:
    values = {
        "mission_id": "mission:1",
        "operation_id": "operation:1",
        "requesting_ocs": "SOFIA",
        "requested_capability": "bounded-capability",
        "bounded_task": "inspect",
        "authority_reference": "authority:1",
        "correlation_id": "correlation:1",
    }
    values.update(changes)
    return AuxiliaryMissionRequest(**values)


def test_p01_binding_is_deterministic_and_does_not_execute() -> None:
    first = bind_auxiliary_mission(request())
    second = bind_auxiliary_mission(request())
    assert first == second
    assert first.parent_mission_id == first.mission_id
    assert first.binding_hash


@pytest.mark.parametrize(
    "field",
    (
        "mission_id",
        "operation_id",
        "requesting_ocs",
        "requested_capability",
        "bounded_task",
        "authority_reference",
        "correlation_id",
    ),
)
def test_n01_missing_required_field_fails_closed(field: str) -> None:
    with pytest.raises(AuxiliaryMissionBindingError):
        bind_auxiliary_mission(request(**{field: ""}))


def test_n02_operation_id_is_not_invented() -> None:
    with pytest.raises(AuxiliaryMissionBindingError):
        bind_auxiliary_mission(request(operation_id=""))


def test_n03_handoff_and_capability_do_not_grant_authority() -> None:
    result = bind_auxiliary_mission(request())
    assert result.authority_reference == "authority:1"
    assert not hasattr(result, "execution_authority_granted")
