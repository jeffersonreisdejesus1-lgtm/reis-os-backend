from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuthorizationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    HOLD = "hold"


class SideEffectClass(StrEnum):
    NONE = "none"
    BOUNDED = "bounded"
    MATERIAL = "material"


class ReversibilityClass(StrEnum):
    REVERSIBLE = "reversible"
    COMPENSATABLE = "compensatable"
    IRREVERSIBLE = "irreversible"


@dataclass(frozen=True)
class Evidence:
    ref: str
    passed: bool
    independent_assurer: str | None = None


@dataclass(frozen=True)
class EvidenceAssessment:
    sufficiency: bool
    deficits: tuple[str, ...]
    contradictions: tuple[str, ...]
    risk_burden: RiskLevel
    evidence_ref: str


@dataclass(frozen=True)
class ActionProposal:
    action_id: str
    actor: str
    ocs: str
    capability: str
    operation: str
    payload: dict[str, object]
    risk: RiskLevel
    lease_id: str | None = None
    evidence: tuple[Evidence, ...] = ()
    action_type: str | None = None
    issued_at: float | None = None
    csp_ref: str | None = None
    object_ref: str | None = None
    tenant: str | None = None
    context_ref: str | None = None
    scope: tuple[str, ...] = ()
    authority_ref: str | None = None
    policy_snapshot: str | None = None
    idempotency_key: str | None = None
    expected_effect: str | None = None
    side_effect_class: SideEffectClass | None = None
    reversibility_class: ReversibilityClass | None = None
    recovery_ref: str | None = None
    expires_at: float | None = None
    evidence_assessment_ref: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class AuthorizedActionEnvelope:
    action_id: str
    actor: str
    ocs: str
    capability: str
    operation: str
    action_type: str
    issued_at: float
    payload: dict[str, object]
    lease_id: str
    evidence_refs: tuple[str, ...]
    csp_ref: str
    object_ref: str
    tenant: str
    context_ref: str
    scope: tuple[str, ...]
    valid_scope: bool
    authority_ref: str
    policy_snapshot: str
    idempotency_key: str
    expected_effect: str
    side_effect_class: SideEffectClass
    reversibility_class: ReversibilityClass
    recovery_ref: str
    expires_at: float
    evidence_assessment_ref: str
    max_uses: int
    trace_id: str
    lease_use_index: int | None = None


@dataclass(frozen=True)
class GovernanceResult:
    decision: AuthorizationDecision
    reason: str
    envelope: AuthorizedActionEnvelope | None = None
    evidence_assessment: EvidenceAssessment | None = None


@dataclass(frozen=True)
class MaterialReadback:
    mutation_id: str
    state: dict[str, object]


@dataclass(frozen=True)
class RecoveryReceipt:
    disposition: str
    state_recovered: bool
    material_compensated: bool
    residual_effect: bool
    external_readback: MaterialReadback | None = None


@dataclass(frozen=True)
class ExecutionResult:
    authorized: bool
    effected: bool
    proven: bool
    reason: str
    readback: MaterialReadback | None = None
    governance_decision: AuthorizationDecision | None = None
    trace_id: str | None = None
    recovery_receipt: RecoveryReceipt | None = None
    residual_effect: bool = False


@dataclass(frozen=True)
class StateRecord:
    state_id: str
    ocs: str
    version: int
    predecessor: str | None
    payload: dict[str, object]
    verified: bool


@dataclass(frozen=True)
class VerifiedCheckpoint:
    checkpoint_id: str
    state: StateRecord


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    action_id: str
    stage: str
    predecessor: str | None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class HandoffReceipt:
    receipt_id: str
    source_ocs: str
    target_ocs: str
    state_ref: str
    authority_transferred: bool = False
    context_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_authority_ref: str = ""

    @property
    def handoff_id(self) -> str:
        return self.receipt_id


@dataclass(frozen=True)
class HandoffAcceptance:
    handoff_id: str
    receiver_ocs: str
    context_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    executable_authority_ref: str | None = None


@dataclass(frozen=True)
class LPEUpdate:
    ocs: str
    category: str
    experience_ref: str
    changes_authority: bool = False
    changes_constitution: bool = False
    imports_autobiography_from_ocs: str | None = None
