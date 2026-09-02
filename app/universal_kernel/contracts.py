from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GovernanceResult(StrEnum):
    AUTHORIZE = "authorize"
    DENY = "deny"
    HOLD = "hold"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    actor: str
    ocs_id: str
    csp_ref: str
    goal_ref: str
    action_type: str
    object_ref: str
    scope_requested: str
    capability_ref: str
    evidence_refs: tuple[str, ...]
    expected_effect: str
    side_effect_class: str
    reversibility_class: str
    context_ref: str
    authority_ref: str | None = None


@dataclass(frozen=True)
class AuthorizedActionEnvelope:
    action_id: str
    actor: str
    ocs_id: str
    csp_ref: str
    object_ref: str
    tenant: str
    context_ref: str
    valid_scope: str
    authority_ref: str
    lease_ref: str
    policy_snapshot: str
    evidence_refs: tuple[str, ...]
    evidence_assessment_ref: str
    idempotency_key: str
    expected_effect: str
    side_effect_class: str
    reversibility_class: str
    recovery_ref: str
    issued_at: int
    expires_at: int
    max_uses: int
    trace_id: str


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    proposal_id: str
    result: GovernanceResult
    reason_codes: tuple[str, ...]
    scope_granted: str | None
    authority_ref: str | None
    lease_ref: str | None
    evidence_assessment_ref: str
    policy_snapshot: str
    validity_window: tuple[int, int] | None
    trace_ref: str
    envelope: AuthorizedActionEnvelope | None = None


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
    requested_scope: str
    prohibited_consequences: tuple[str, ...]
    predecessor_receipt_ref: str
    authority_transfer: bool = False

    def __post_init__(self) -> None:
        if self.authority_transfer:
            raise ValueError("handoff may not transfer authority")
