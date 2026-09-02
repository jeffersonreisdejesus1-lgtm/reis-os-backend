from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GovernanceResult(str, Enum):
    AUTHORIZE = "authorize"
    DENY = "deny"
    HOLD = "hold"
    ESCALATE = "escalate"


class SideEffectClass(str, Enum):
    READ_ONLY = "read_only"
    LOCAL_MUTATION = "local_mutation"
    PERSISTENT_MUTATION = "persistent_mutation"
    EXTERNAL_CALL = "external_call"
    MESSAGE_SEND = "message_send"
    PUBLICATION = "publication"
    SPEND = "spend"
    POLICY_CHANGE = "policy_change"
    INSTITUTIONAL_STATE_CHANGE = "institutional_state_change"


class ReversibilityClass(str, Enum):
    NONE = "none"
    STATE_ONLY = "state_only"
    REVERSIBLE_EXTERNAL = "reversible_external"
    IRREVERSIBLE_OR_PARTIAL = "irreversible_or_partial"


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    actor: str
    ocs_id: str
    csp_ref: str
    goal_ref: str
    action_type: str
    object_ref: str
    scope_requested: tuple[str, ...]
    capability_ref: str
    evidence_refs: tuple[str, ...]
    expected_effect: str
    side_effect_class: SideEffectClass
    reversibility_class: ReversibilityClass
    context_ref: str


@dataclass(frozen=True)
class ConstitutionSnapshot:
    constitution_ref: str
    policy_version: str
    inherited_prohibitions: tuple[str, ...]
    authority_ceiling: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True)
class IdentityContext:
    ocs_id: str
    identity: str
    ancestry: tuple[str, ...]
    predecessor: str | None
    constitution_ref: str


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    adapter_id: str
    side_effect_class: SideEffectClass
    required_scope: tuple[str, ...]
    reversibility: ReversibilityClass
    idempotency_support: bool
    readback_support: bool
    credential_class: str


@dataclass(frozen=True)
class EvidenceAssessment:
    assessment_id: str
    adequate: bool
    provenance: bool = True
    reliability: bool = True
    freshness: bool = True
    independence: bool = True
    contradiction_control: bool = True
    scope_fit: bool = True
    auditability: bool = True
    reason_codes: tuple[str, ...] = ()


@dataclass
class AuthorityLease:
    lease_ref: str
    actor: str
    ocs_id: str
    action: str
    object_ref: str
    scope: tuple[str, ...]
    context_ref: str
    issued_at: int
    expires_at: int
    max_uses: int = 1
    uses: int = 0
    revoked: bool = False
    transferable: bool = False

    def is_active(self, now: int) -> bool:
        return not self.revoked and now <= self.expires_at and self.uses < self.max_uses


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    proposal_id: str
    result: GovernanceResult
    reason_codes: tuple[str, ...]
    scope_granted: tuple[str, ...] = ()
    authority_ref: str | None = None
    lease_ref: str | None = None
    evidence_assessment_ref: str | None = None
    policy_snapshot: str | None = None
    validity_window: tuple[int, int] | None = None
    trace_ref: str | None = None


@dataclass(frozen=True)
class AuthorizedActionEnvelope:
    action_id: str
    actor: str
    ocs_id: str
    csp_ref: str
    object_ref: str
    tenant: str
    context_ref: str
    valid_scope: tuple[str, ...]
    authority_ref: str
    lease_ref: str
    policy_snapshot: str
    evidence_refs: tuple[str, ...]
    evidence_assessment_ref: str
    idempotency_key: str
    expected_effect: str
    side_effect_class: SideEffectClass
    reversibility_class: ReversibilityClass
    recovery_ref: str
    issued_at: int
    expires_at: int
    max_uses: int
    trace_id: str


@dataclass(frozen=True)
class EffectAttemptResult:
    action_id: str
    attempted: bool
    provider_ref: str | None
    result_class: str
    mutation_observed: bool
    mutation_count: int
    readback_ref: str | None
    error_ref: str | None
    started_at: int
    ended_at: int
    trace_ref: str


@dataclass(frozen=True)
class StateCommitRecord:
    state_namespace: str
    version: int
    predecessor_version: int | None
    content_hash: str
    write_set_ref: str
    authority_ref: str
    action_id: str
    readback_hash: str
    committed_at: int
    checkpoint_ref: str | None
    trace_ref: str


@dataclass(frozen=True)
class HandoffPackage:
    handoff_id: str
    from_ocs: str
    to_ocs: str
    object_ref: str
    context_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    open_findings: tuple[str, ...]
    requested_scope: tuple[str, ...]
    prohibited_consequences: tuple[str, ...]
    predecessor_receipt_ref: str
    authority_transfer: bool = False


@dataclass(frozen=True)
class Receipt:
    object_ref: str
    status: str
    reservations: tuple[str, ...]
    next_ocs: str | None
    authorized_next_scope: str | None
    prohibited_consequences: tuple[str, ...]


@dataclass(frozen=True)
class PIActivation:
    pi_id: str
    activation_class: str
    reason: str
    producer: str
    consumer: str
    decision_contribution: str


@dataclass(frozen=True)
class OCSProfile:
    ocs_id: str
    identity: str
    ancestry: tuple[str, ...]
    constitution_ref: str
    csp_ref: str
    specialty: str
    authority_envelope: tuple[str, ...]
    state_namespace: str
    memory_namespace: str
    version: str
    predecessor: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
