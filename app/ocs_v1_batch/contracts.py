from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class OCSV1InvariantError(RuntimeError):
    pass


class EvidenceState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


class DecisionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class GovernorSpec:
    governor_id: str
    role: str
    writable_namespaces: tuple[str, ...]
    owned_state_keys: tuple[str, ...]
    allowed_operations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    ocs_id: str
    identity_ref: str
    derivation_ref: str
    specialization: str
    governors: tuple[GovernorSpec, ...]
    binding_refs: Mapping[str, str]
    namespaces: tuple[str, ...]
    deterministic_policies: tuple[str, ...]
    preserved_reservations: tuple[str, ...] = ()

    def validate(self) -> None:
        governor_ids = {g.governor_id for g in self.governors}
        if len(self.governors) != 4 or len(governor_ids) != 4:
            raise OCSV1InvariantError(f"{self.ocs_id}:LOCAL_GOVERNOR_ROSTER_INVALID")
        if len(self.binding_refs) != 6 or set(self.binding_refs) != {f"R{i}_R7_BINDING_REF" for i in range(1, 7)}:
            raise OCSV1InvariantError(f"{self.ocs_id}:R1_R6_BINDINGS_INVALID")
        if len(self.namespaces) != len(set(self.namespaces)):
            raise OCSV1InvariantError(f"{self.ocs_id}:DUPLICATE_NAMESPACE")
        seen: set[str] = set()
        for governor in self.governors:
            if not governor.owned_state_keys or not governor.allowed_operations:
                raise OCSV1InvariantError(f"{self.ocs_id}:GOVERNOR_CONTRACT_INCOMPLETE")
            if not set(governor.writable_namespaces).issubset(self.namespaces):
                raise OCSV1InvariantError(f"{self.ocs_id}:GOVERNOR_NAMESPACE_INVALID")
            overlap = seen.intersection(governor.owned_state_keys)
            if overlap:
                raise OCSV1InvariantError(f"{self.ocs_id}:DUPLICATE_STATE_OWNER")
            seen.update(governor.owned_state_keys)


@dataclass(frozen=True, slots=True)
class GovernanceRequest:
    request_id: str
    ocs_id: str
    governor_id: str
    operation: str
    namespace: str
    mutation: Mapping[str, object] = field(default_factory=dict)
    expected_state_version: int = 0
    evidence_state: EvidenceState = EvidenceState.UNKNOWN
    evidence_ref: str | None = None
    provenance_ref: str | None = None
    object_ref: str | None = None
    exact_head: str | None = None
    authority_ref: str | None = None
    self_assurance_requested: bool = False
    promotion_requested: bool = False
    runtime_activation_requested: bool = False
    authority_transfer_requested: bool = False
    external_write_requested: bool = False
    package_id: str | None = None
    return_receipt_package_id: str | None = None
    superseded_specialty_requested: bool = False
    historical_provenance_claimed_resolved: bool = False
    strategy_as_execution_authority: bool = False
    communication_as_institutional_authority: bool = False


@dataclass(frozen=True, slots=True)
class GovernanceReceipt:
    request_id: str
    ocs_id: str
    status: DecisionStatus
    reason: str
    mutation_count: int
    state_version_before: int
    state_version_after: int
    identity_ref: str
    derivation_ref: str
