from types import SimpleNamespace

import pytest

from app.ocs_instances.contracts import InstanceStatus
from app.ocs_instances.ib9_h06_authoritative_binding import IB9H06AuthoritativeBindingRuntime, IB9H06ReconciliationStep, IB9H06StopCondition


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (InstanceStatus.PREPARED, IB9H06ReconciliationStep.ATTACH_WORK_RECEIPT),
        (InstanceStatus.PERSISTED, IB9H06ReconciliationStep.ATTACH_WORK_RECEIPT),
        (InstanceStatus.BOUND, IB9H06ReconciliationStep.ACKNOWLEDGE_BOOTSTRAP),
        (InstanceStatus.ACTIVE, IB9H06ReconciliationStep.CHECKPOINT),
        (InstanceStatus.CHECKPOINTED, IB9H06ReconciliationStep.REPLACE),
        (InstanceStatus.REPLACED, IB9H06ReconciliationStep.RECOVER),
        (InstanceStatus.CLOSED, IB9H06ReconciliationStep.HOLD),
        (InstanceStatus.HOLD, IB9H06ReconciliationStep.HOLD),
    ],
)
def test_ib9_h06_next_valid_step_is_derived_from_registry_status(status, expected):
    binding = SimpleNamespace(status=status)
    assert IB9H06AuthoritativeBindingRuntime.next_valid_step(binding) is expected


def test_ib9_h06_stop_conditions_are_explicit_and_finite():
    conditions = IB9H06AuthoritativeBindingRuntime.stop_conditions()
    assert IB9H06StopCondition.AUTHORITY_UNKNOWN in conditions
    assert IB9H06StopCondition.COMMAND_MUTATION_REQUESTED in conditions
    assert len(conditions) == len(IB9H06StopCondition)


def test_ib9_h06_facade_does_not_expose_command_mutation():
    assert not any(
        name.startswith(("create", "update", "delete", "mutate"))
        for name in dir(IB9H06AuthoritativeBindingRuntime)
    )
