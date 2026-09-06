from types import SimpleNamespace

import pytest

from app.ocs_instances.contracts import InstanceStatus
from app.ocs_instances.ib10 import IB10IntegrationRuntime, IB10Step, IB10StopCondition


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (InstanceStatus.PREPARED, IB10Step.ATTACH_WORK_RECEIPT),
        (InstanceStatus.PERSISTED, IB10Step.ATTACH_WORK_RECEIPT),
        (InstanceStatus.BOUND, IB10Step.ACKNOWLEDGE_BOOTSTRAP),
        (InstanceStatus.ACTIVE, IB10Step.CHECKPOINT),
        (InstanceStatus.CHECKPOINTED, IB10Step.REPLACE),
        (InstanceStatus.REPLACED, IB10Step.RECOVER),
        (InstanceStatus.CLOSED, IB10Step.HOLD),
        (InstanceStatus.HOLD, IB10Step.HOLD),
    ],
)
def test_ib10_next_valid_step_is_derived_from_registry_status(status, expected):
    binding = SimpleNamespace(status=status)
    assert IB10IntegrationRuntime.next_valid_step(binding) is expected


def test_ib10_stop_conditions_are_explicit_and_finite():
    conditions = IB10IntegrationRuntime.stop_conditions()
    assert IB10StopCondition.AUTHORITY_UNKNOWN in conditions
    assert IB10StopCondition.COMMAND_MUTATION_REQUESTED in conditions
    assert len(conditions) == len(IB10StopCondition)


def test_ib10_facade_does_not_expose_command_mutation():
    assert not any(
        name.startswith(("create", "update", "delete", "mutate"))
        for name in dir(IB10IntegrationRuntime)
    )
