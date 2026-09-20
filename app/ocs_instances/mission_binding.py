"""P01 binding from a canonical mission envelope to the auxiliary runtime."""
from __future__ import annotations

from dataclasses import dataclass

from app.ocs_instances.contracts import canonical_hash


class AuxiliaryMissionBindingError(ValueError):
    """Raised when a mission envelope is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class AuxiliaryMissionRequest:
    mission_id: str
    operation_id: str
    requesting_ocs: str
    requested_capability: str
    bounded_task: str
    authority_reference: str
    correlation_id: str
    causation_id: str | None = None
    parent_mission_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuxiliaryMissionBindingResult:
    mission_id: str
    operation_id: str
    requesting_ocs: str
    requested_capability: str
    bounded_task: str
    authority_reference: str
    correlation_id: str
    causation_id: str | None
    parent_mission_id: str
    binding_hash: str


def bind_auxiliary_mission(
    request: AuxiliaryMissionRequest,
) -> AuxiliaryMissionBindingResult:
    """Validate and deterministically bind a mission without executing it."""
    required = (
        request.mission_id,
        request.operation_id,
        request.requesting_ocs,
        request.requested_capability,
        request.bounded_task,
        request.authority_reference,
        request.correlation_id,
    )
    if not all(required):
        raise AuxiliaryMissionBindingError("auxiliary_mission_fields_required")
    parent_mission_id = request.parent_mission_id or request.mission_id
    payload = {
        "mission_id": request.mission_id,
        "operation_id": request.operation_id,
        "requesting_ocs": request.requesting_ocs,
        "requested_capability": request.requested_capability,
        "bounded_task": request.bounded_task,
        "authority_reference": request.authority_reference,
        "correlation_id": request.correlation_id,
        "causation_id": request.causation_id,
        "parent_mission_id": parent_mission_id,
    }
    return AuxiliaryMissionBindingResult(
        mission_id=request.mission_id,
        operation_id=request.operation_id,
        requesting_ocs=request.requesting_ocs,
        requested_capability=request.requested_capability,
        bounded_task=request.bounded_task,
        authority_reference=request.authority_reference,
        correlation_id=request.correlation_id,
        causation_id=request.causation_id,
        parent_mission_id=parent_mission_id,
        binding_hash=canonical_hash(payload),
    )
