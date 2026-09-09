from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class SynesisInvariantError(RuntimeError):
    pass


class EvidenceState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"
    PARTIAL = "PARTIAL"


class DecisionStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_RESERVATIONS = "PASS_WITH_RESERVATIONS"
    HOLD = "HOLD"
    FINDING = "FINDING"
    DENIED = "DENIED"


@dataclass(frozen=True)
class GovernorSpec:
    governor_id: str
    role: str
    writable_namespaces: tuple[str, ...]
    owned_state_keys: tuple[str, ...]
    allowed_operations: tuple[str, ...]


@dataclass(frozen=True)
class SynesisProfile:
    ocs_id: str = "SYNESIS"
    identity_ref: str = "REIS OS — Evolution Core — Sýnesis / 3c9d31bc-7b67-816f-b7b2-d56f4a408ec6"
    architecture_ref: str = "SYNESIS-V1-LOCAL-REFACTOR-ARCHITECTURE-001"
    assurance_ref: str = "NOESIS-SYNESIS-V1-A2-REASSURANCE-002"
    i0_ref: str = "SYNESIS-V1-IMPLEMENTATION-ARCHITECTURE-I0-001"
    excluded_predecessor: str = "REF-SYNESIS-LOCAL-001"
    preserved_reservations: tuple[str, ...] = (
        "N_SYN_RUNTIME_ASSURANCE=HOLD_NON_BLOCKING",
        "ANATOMICAL_PARITY=UNPROVEN",
        "DEEP_ANATOMICAL_PARITY_PROVEN=0/10",
        "CR3_GLOBAL_FUNCTIONAL_PLENITUDE=NOT_PROVEN",
        "GLOBAL_REAL_OCS_GOVERNANCE=NOT_PROVEN_WHERE_PREVIOUSLY_RESERVED",
    )
    binding_refs: Mapping[str, str] = field(default_factory=lambda: {
        "R1_R7": "SYNESIS-V1-R1-R7-ASSURANCE-STATE-CONTRACT-001",
        "R2_R7": "SYNESIS-V1-R2-R7-COVERAGE-EFFECTIVENESS-CONTRACT-001",
        "R3_R7": "SYNESIS-V1-R3-R7-ASSURANCE-TRANSITION-CONTRACT-001",
        "R4_R7": "SYNESIS-V1-R4-R7-ASSURANCE-SCHEDULING-CONTRACT-001",
        "R5_R7": "SYNESIS-V1-R5-R7-EVIDENCE-PROVENANCE-CONTRACT-001",
        "R6_R7": "SYNESIS-V1-R6-R7-INDEPENDENCE-AUTHORITY-CONTRACT-001",
    })
    governors: tuple[GovernorSpec, ...] = (
        GovernorSpec(
            governor_id="GOV-SYNESIS-01",
            role="ASSURANCE_INTAKE_INDEPENDENCE_GOVERNOR",
            writable_namespaces=("synesis.v1.assurance.intake",),
            owned_state_keys=("object_ref", "exact_revision", "independence_state"),
            allowed_operations=("REGISTER_ASSURANCE_INTAKE",),
        ),
        GovernorSpec(
            governor_id="GOV-SYNESIS-02",
            role="EVIDENCE_SUFFICIENCY_PROVENANCE_GOVERNOR",
            writable_namespaces=("synesis.v1.assurance.evidence",),
            owned_state_keys=("evidence_ref", "provenance_ref", "evidence_state"),
            allowed_operations=("CLASSIFY_EVIDENCE",),
        ),
        GovernorSpec(
            governor_id="GOV-SYNESIS-03",
            role="CLAIM_RESERVATION_FINDING_GOVERNOR",
            writable_namespaces=("synesis.v1.assurance.disposition",),
            owned_state_keys=("claim_ref", "disposition", "reservation_refs", "finding_refs"),
            allowed_operations=("CLASSIFY_DISPOSITION",),
        ),
        GovernorSpec(
            governor_id="GOV-SYNESIS-04",
            role="REASSURANCE_ROUTING_RECOVERY_GOVERNOR",
            writable_namespaces=("synesis.v1.assurance.routing",),
            owned_state_keys=("route_ref", "reassurance_required", "recovery_ref"),
            allowed_operations=("ROUTE_REASSURANCE",),
        ),
    )

    def validate(self) -> None:
        if len(self.governors) != 4:
            raise SynesisInvariantError("SYNESIS:LOCAL_GOVERNOR_COUNT_MISMATCH")
        if set(self.binding_refs) != {"R1_R7", "R2_R7", "R3_R7", "R4_R7", "R5_R7", "R6_R7"}:
            raise SynesisInvariantError("SYNESIS:R1_R6_BINDING_SET_MISMATCH")
        if any(not g.governor_id.startswith("GOV-SYNESIS-") for g in self.governors):
            raise SynesisInvariantError("SYNESIS:FOREIGN_GOVERNOR_ID")


@dataclass(frozen=True)
class AssuranceRequest:
    request_id: str
    ocs_id: str
    governor_id: str
    operation: str
    namespace: str
    mutation: Mapping[str, object]
    expected_state_version: int
    expected_generation: int
    object_ref: str | None = None
    exact_revision: str | None = None
    evidence_state: EvidenceState = EvidenceState.UNKNOWN
    evidence_ref: str | None = None
    provenance_ref: str | None = None
    claim_ref: str | None = None
    requested_disposition: DecisionStatus | None = None
    reservation_refs: tuple[str, ...] = ()
    self_assurance_requested: bool = False
    self_homologation_requested: bool = False
    promotion_requested: bool = False
    runtime_activation_requested: bool = False
    authority_transfer_requested: bool = False
    predecessor_ref: str | None = None


@dataclass(frozen=True)
class AssuranceReceipt:
    request_id: str
    status: DecisionStatus
    reason: str
    mutation_count: int
    state_version_before: int
    state_version_after: int
    generation: int
