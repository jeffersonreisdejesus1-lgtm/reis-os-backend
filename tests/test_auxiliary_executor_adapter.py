from dataclasses import dataclass

from app.ocs_instances.executor_adapter import (
    AuxiliaryExecutionRequest,
    AuxiliaryExecutionResult,
    ExecutorOutcome,
    bind_executor,
    normalize_executor_error,
)
from app.ocs_instances.mission_binding import (
    AuxiliaryMissionBindingResult,
    AuxiliaryMissionRequest,
    bind_auxiliary_mission,
)


@dataclass(frozen=True)
class FakeExecutor:
    executor_id: str = "executor:test"
    capabilities: frozenset[str] = frozenset({"bounded-capability"})


def binding() -> AuxiliaryMissionBindingResult:
    return bind_auxiliary_mission(
        AuxiliaryMissionRequest(
            mission_id="mission:1",
            operation_id="operation:1",
            requesting_ocs="SOFIA",
            requested_capability="bounded-capability",
            bounded_task="inspect",
            authority_reference="authority:1",
            correlation_id="correlation:1",
        )
    )


def test_p02_accepts_executor_only_after_authority_binding() -> None:
    result = bind_executor(
        binding(), FakeExecutor(),
        authorized_capabilities=frozenset({"bounded-capability"}),
        timeout_seconds=5,
    )
    assert isinstance(result, AuxiliaryExecutionRequest)
    assert result.authority_reference == "authority:1"


def test_executor_absent_is_fail_closed() -> None:
    result = bind_executor(
        binding(), None,
        authorized_capabilities=frozenset({"bounded-capability"}),
        timeout_seconds=5,
    )
    assert isinstance(result, AuxiliaryExecutionResult)
    assert result.outcome is ExecutorOutcome.FAIL_CLOSED
    assert result.error_code == "executor_absent"


def test_capability_outside_authorized_scope_is_rejected() -> None:
    result = bind_executor(
        binding(),
        FakeExecutor(),
        authorized_capabilities=frozenset(),
        timeout_seconds=5,
    )
    assert isinstance(result, AuxiliaryExecutionResult)
    assert result.outcome is ExecutorOutcome.FAIL_CLOSED


def test_timeout_is_explicit_and_no_dispatch_occurs() -> None:
    result = bind_executor(
        binding(),
        FakeExecutor(),
        authorized_capabilities=frozenset({"bounded-capability"}),
        timeout_seconds=0,
    )
    assert isinstance(result, AuxiliaryExecutionResult)
    assert result.outcome is ExecutorOutcome.TIMEOUT


def test_executor_error_cannot_become_success() -> None:
    result = normalize_executor_error(binding(), FakeExecutor(), RuntimeError("boom"))
    assert result.outcome is ExecutorOutcome.ERROR
    assert result.error_code == "RuntimeError"
