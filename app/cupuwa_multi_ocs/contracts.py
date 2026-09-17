from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContractViolation(ValueError):
    """Raised when a multi-OCS contract violates a canonical invariant."""


class ReconciliationState(StrEnum):
    CONSISTENT = "CONSISTENT"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"
    HOLD = "HOLD"


def _require(value: str, name: str) -> None:
    if not value.strip():
        raise ContractViolation(f"{name}_required")


def _require_tuple(value: tuple[str, ...], name: str) -> None:
    if not value or any(not item.strip() for item in value):
        raise ContractViolation(f"{name}_required")


@dataclass(frozen=True, slots=True)
class MissionContract:
    mission_id: str
    product: str
    increment_id: str
    bound_object: str
    bound_head: str
    requested_outcome: str
    constraints: tuple[str, ...]
    authority_ref: str
    required_capabilities: tuple[str, ...]
    evidence_policy: str
    completion_policy: str

    def __post_init__(self) -> None:
        for name in (
            "mission_id",
            "product",
            "increment_id",
            "bound_object",
            "bound_head",
            "requested_outcome",
            "authority_ref",
            "evidence_policy",
            "completion_policy",
        ):
            _require(getattr(self, name), name)
        _require_tuple(self.required_capabilities, "required_capabilities")


@dataclass(frozen=True, slots=True)
class SpecialistHandoff:
    mission_id: str
    source_ocs: str
    target_ocs: str
    bound_object: str
    bound_head: str
    scope: tuple[str, ...]
    inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    authority_envelope_ref: str
    required_capabilities: tuple[str, ...]
    tool_permissions: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    failure_state: str
    predecessor_receipts: tuple[str, ...] = ()
    authority_transfer: bool = False
    memory_import: bool = False
    material_effect_claim: bool = False

    def __post_init__(self) -> None:
        for name in (
            "mission_id",
            "source_ocs",
            "target_ocs",
            "bound_object",
            "bound_head",
            "authority_envelope_ref",
            "failure_state",
        ):
            _require(getattr(self, name), name)
        for name in (
            "scope",
            "expected_outputs",
            "required_capabilities",
            "evidence_requirements",
            "completion_criteria",
        ):
            _require_tuple(getattr(self, name), name)
        if self.authority_transfer:
            raise ContractViolation("authority_transfer_prohibited")
        if self.memory_import:
            raise ContractViolation("cross_ocs_memory_import_prohibited")
        if self.material_effect_claim:
            raise ContractViolation("handoff_material_effect_claim_prohibited")
        if self.tool_permissions:
            raise ContractViolation("contract_layer_tool_permissions_prohibited")

    def validate_against(self, mission: MissionContract) -> None:
        if self.mission_id != mission.mission_id:
            raise ContractViolation("mission_identity_drift")
        if self.bound_head != mission.bound_head:
            raise ContractViolation("bound_head_drift")
        if self.bound_object != mission.bound_object:
            raise ContractViolation("bound_object_drift")
        if self.authority_envelope_ref != mission.authority_ref:
            raise ContractViolation("authority_reference_drift")


@dataclass(frozen=True, slots=True)
class SpecialistReceipt:
    mission_id: str
    ocs_id: str
    bound_head: str
    produced_outputs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    status: str
    predecessor_receipts: tuple[str, ...] = ()
    authority_granted: bool = False
    material_effect_claim: bool = False

    def __post_init__(self) -> None:
        for name in ("mission_id", "ocs_id", "bound_head", "status"):
            _require(getattr(self, name), name)
        _require_tuple(self.produced_outputs, "produced_outputs")
        if self.authority_granted:
            raise ContractViolation("receipt_authority_grant_prohibited")
        if self.material_effect_claim:
            raise ContractViolation("receipt_material_effect_claim_prohibited")
        if not self.evidence_refs:
            raise ContractViolation("receipt_evidence_required")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    mission_id: str
    bound_head: str
    state: ReconciliationState
    accepted_receipts: tuple[str, ...]
    findings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require(self.mission_id, "mission_id")
        _require(self.bound_head, "bound_head")
        if not isinstance(self.state, ReconciliationState):
            raise ContractViolation("invalid_reconciliation_state")
        if self.state is ReconciliationState.CONSISTENT:
            _require_tuple(self.accepted_receipts, "accepted_receipts")

    @property
    def executable(self) -> bool:
        return self.state is ReconciliationState.CONSISTENT


@dataclass(frozen=True, slots=True)
class ImplementationContract:
    mission_id: str
    bound_head: str
    accepted_decisions: tuple[str, ...]
    decision_evidence_refs: tuple[str, ...]
    unresolved_findings: tuple[str, ...]
    implementation_scope: tuple[str, ...]
    required_effect_capabilities: tuple[str, ...]
    authority_envelope_ref: str
    lease_requirements: tuple[str, ...]
    required_tests: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    reconciliation: ReconciliationResult

    def __post_init__(self) -> None:
        _require(self.mission_id, "mission_id")
        _require(self.bound_head, "bound_head")
        _require(self.authority_envelope_ref, "authority_envelope_ref")
        for name in (
            "accepted_decisions",
            "decision_evidence_refs",
            "implementation_scope",
            "required_effect_capabilities",
            "lease_requirements",
            "required_tests",
            "evidence_requirements",
        ):
            _require_tuple(getattr(self, name), name)
        if self.reconciliation.mission_id != self.mission_id:
            raise ContractViolation("reconciliation_mission_identity_drift")
        if self.reconciliation.bound_head != self.bound_head:
            raise ContractViolation("reconciliation_bound_head_drift")

    @property
    def execution_allowed(self) -> bool:
        return self.reconciliation.executable and not self.unresolved_findings
