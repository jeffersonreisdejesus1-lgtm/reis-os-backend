from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


IRIS_IDENTITY_STATE_ROOT = "EC-IRIS-GENERALIST-EVO-001 + IRIS_STATE.json"
IRIS_DESIGN_AUTHORITY = "IRIS"
IRIS_DERIVATION_REF = "IRIS-V1-LOCAL-GOVERNOR-DERIVATION-001"

LOCAL_GOVERNOR_IDS = frozenset({
    "GOV-IRIS-01",
    "GOV-IRIS-02",
    "GOV-IRIS-03",
    "GOV-IRIS-04",
})

REQUIRED_BINDING_REFS = (
    "R1_R7_BINDING_REF",
    "R2_R7_BINDING_REF",
    "R3_R7_BINDING_REF",
    "R4_R7_BINDING_REF",
    "R5_R7_BINDING_REF",
    "R6_R7_BINDING_REF",
)


class IrisV1InvariantError(RuntimeError):
    pass


class EvidenceFreshness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


class DecisionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class IrisV1Bindings:
    refs: Mapping[str, str]

    @classmethod
    def materialized(cls) -> "IrisV1Bindings":
        return cls(
            refs={
                "R1_R7_BINDING_REF": "IRIS-V1-R1-R7-STATE-CONTRACT-001",
                "R2_R7_BINDING_REF": "IRIS-V1-R2-R7-MEASUREMENT-CONTRACT-001",
                "R3_R7_BINDING_REF": "IRIS-V1-R3-R7-TRANSITION-CONTRACT-001",
                "R4_R7_BINDING_REF": "IRIS-V1-R4-R7-SCHEDULING-CONTRACT-001",
                "R5_R7_BINDING_REF": "IRIS-V1-R5-R7-OBSERVATION-CONTRACT-001",
                "R6_R7_BINDING_REF": "IRIS-V1-R6-R7-CONSTRAINT-CONTRACT-001",
            }
        )

    def assert_complete(self) -> None:
        missing = [name for name in REQUIRED_BINDING_REFS if not self.refs.get(name)]
        if missing:
            raise IrisV1InvariantError(
                "IRIS_V1_R1_R6_BINDINGS_INCOMPLETE:" + ",".join(missing)
            )


@dataclass(frozen=True, slots=True)
class GovernorSpec:
    governor_id: str
    role: str
    requirements: tuple[str, ...]
    writable_namespaces: tuple[str, ...]
    readable_namespaces: tuple[str, ...]
    authority_ceiling: str = IRIS_DESIGN_AUTHORITY

    def validate(self) -> None:
        if self.governor_id not in LOCAL_GOVERNOR_IDS:
            raise IrisV1InvariantError("IRIS_V1_GOVERNOR_NOT_DERIVED")
        if self.authority_ceiling != IRIS_DESIGN_AUTHORITY:
            raise IrisV1InvariantError("IRIS_V1_AUTHORITY_EXPANSION_FORBIDDEN")


@dataclass(slots=True)
class GovernorLease:
    lease_id: str
    mission_id: str
    governor_id: str
    scope: tuple[str, ...]
    generation: int
    valid_from: float
    expires_at: float
    authority_ref: str = IRIS_DESIGN_AUTHORITY
    fenced: bool = False


@dataclass(frozen=True, slots=True)
class GovernanceRequest:
    request_id: str
    mission_id: str
    governor_id: str
    operation: str
    namespace: str
    mutation: Mapping[str, object] = field(default_factory=dict)
    expected_state_version: int = 0
    lease_id: str | None = None
    generation: int = 1
    evidence_freshness: EvidenceFreshness = EvidenceFreshness.UNKNOWN
    accessibility_conflict: bool = False
    design_approval_claimed: bool = False
    authority_transfer_requested: bool = False
    material_effect_requested: bool = False


@dataclass(frozen=True, slots=True)
class GovernanceReceipt:
    request_id: str
    status: DecisionStatus
    reason: str
    mutation_count: int
    state_version_before: int
    state_version_after: int
    design_authority: str = IRIS_DESIGN_AUTHORITY
    identity_state_root: str = IRIS_IDENTITY_STATE_ROOT
