"""P02 executor boundary; validation only, with no material dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.ocs_instances.mission_binding import (
    AuxiliaryMissionBindingResult,
)


class AuxiliaryExecutor(Protocol):
    @property
    def executor_id(self) -> str: ...

    @property
    def capabilities(self) -> frozenset[str]: ...


class ExecutorOutcome(StrEnum):
    READY = "ready"
    FAIL_CLOSED = "fail_closed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AuxiliaryExecutionRequest:
    operation_id: str
    mission_id: str
    capability: str
    bounded_task: str
    authority_reference: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class AuxiliaryExecutionResult:
    outcome: ExecutorOutcome
    executor_id: str | None
    operation_id: str
    error_code: str | None = None


def bind_executor(
    binding: AuxiliaryMissionBindingResult,
    executor: AuxiliaryExecutor | None,
    *,
    authorized_capabilities: frozenset[str],
    timeout_seconds: float,
) -> AuxiliaryExecutionRequest | AuxiliaryExecutionResult:
    """Validate an executor boundary without dispatching material work."""
    if executor is None:
        return AuxiliaryExecutionResult(
            ExecutorOutcome.FAIL_CLOSED, None, binding.operation_id, "executor_absent"
        )
    if binding.requested_capability not in authorized_capabilities:
        return AuxiliaryExecutionResult(
            ExecutorOutcome.FAIL_CLOSED,
            executor.executor_id,
            binding.operation_id,
            "capability_not_authorized",
        )
    if binding.requested_capability not in executor.capabilities:
        return AuxiliaryExecutionResult(
            ExecutorOutcome.FAIL_CLOSED,
            executor.executor_id,
            binding.operation_id,
            "capability_not_supported",
        )
    if timeout_seconds <= 0:
        return AuxiliaryExecutionResult(
            ExecutorOutcome.TIMEOUT,
            executor.executor_id,
            binding.operation_id,
            "timeout_invalid",
        )
    return AuxiliaryExecutionRequest(
        operation_id=binding.operation_id,
        mission_id=binding.mission_id,
        capability=binding.requested_capability,
        bounded_task=binding.bounded_task,
        authority_reference=binding.authority_reference,
        timeout_seconds=timeout_seconds,
    )


def normalize_executor_error(
    binding: AuxiliaryMissionBindingResult,
    executor: AuxiliaryExecutor | None,
    error: BaseException,
) -> AuxiliaryExecutionResult:
    """Convert an executor failure to an explicit non-success result."""
    return AuxiliaryExecutionResult(
        ExecutorOutcome.ERROR,
        executor.executor_id if executor is not None else None,
        binding.operation_id,
        type(error).__name__,
    )
