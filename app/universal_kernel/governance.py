from __future__ import annotations

import time
from dataclasses import dataclass, replace

from .contracts import (
    ActionProposal,
    AuthorizedActionEnvelope,
    GovernanceDecision,
    GovernanceResult,
)
from .trace import TraceLedger


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    adapter_id: str
    side_effect_class: str
    required_scope: str
    reversibility: str
    idempotency_support: bool
    readback_support: bool


class CapabilityRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        self._descriptors[descriptor.capability_id] = descriptor

    def describe(self, capability_id: str) -> CapabilityDescriptor:
        return self._descriptors[capability_id]


@dataclass(frozen=True)
class EvidenceAssessment:
    assessment_ref: str
    sufficient: bool
    reason_codes: tuple[str, ...]
    independent_assurance: bool = False


class EvidenceEngine:
    def assess(
        self,
        *,
        proposal: ActionProposal,
        required: bool,
        passing_refs: set[str],
        self_assurance_claimed: bool = False,
    ) -> EvidenceAssessment:
        if self_assurance_claimed:
            return EvidenceAssessment(
                assessment_ref=f"evidence://{proposal.proposal_id}",
                sufficient=False,
                reason_codes=("SELF_ASSURANCE_DENIED",),
            )
        if not required:
            return EvidenceAssessment(
                assessment_ref=f"evidence://{proposal.proposal_id}",
                sufficient=True,
                reason_codes=("BURDEN_NOT_REQUIRED",),
            )
        sufficient = bool(proposal.evidence_refs) and all(
            ref in passing_refs for ref in proposal.evidence_refs
        )
        return EvidenceAssessment(
            assessment_ref=f"evidence://{proposal.proposal_id}",
            sufficient=sufficient,
            reason_codes=("EVIDENCE_OK",) if sufficient else ("EVIDENCE_INSUFFICIENT",),
        )


@dataclass(frozen=True)
class AuthorityLease:
    lease_ref: str
    authority_ref: str
    actor: str
    ocs_id: str
    action_type: str
    object_ref: str
    scope: str
    context_ref: str
    expires_at: int
    max_uses: int
    used: int = 0
    revoked: bool = False

    @property
    def active(self) -> bool:
        return (
            not self.revoked
            and self.used < self.max_uses
            and int(time.time()) < self.expires_at
        )


class AuthorityLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, AuthorityLease] = {}

    def grant(self, lease: AuthorityLease) -> None:
        self._leases[lease.lease_ref] = lease

    def get(self, lease_ref: str) -> AuthorityLease:
        return self._leases[lease_ref]

    def find_for_proposal(self, proposal: ActionProposal) -> AuthorityLease | None:
        for item in self._leases.values():
            if (
                item.authority_ref == proposal.authority_ref
                and item.actor == proposal.actor
                and item.ocs_id == proposal.ocs_id
                and item.action_type == proposal.action_type
                and item.object_ref == proposal.object_ref
                and item.scope == proposal.scope_requested
                and item.context_ref == proposal.context_ref
            ):
                return item
        return None

    def revoke(self, lease_ref: str) -> None:
        lease = self.get(lease_ref)
        self._leases[lease_ref] = replace(lease, revoked=True)

    def consume(self, lease_ref: str) -> AuthorityLease:
        lease = self.get(lease_ref)
        if not lease.active:
            raise PermissionError("lease inactive")
        consumed = replace(lease, used=lease.used + 1)
        self._leases[lease_ref] = consumed
        return consumed


class GovernanceEngine:
    def __init__(
        self,
        registry: CapabilityRegistry,
        leases: AuthorityLeaseManager,
        trace: TraceLedger,
    ) -> None:
        self._registry = registry
        self._leases = leases
        self._trace = trace

    def decide(
        self,
        *,
        proposal: ActionProposal,
        assessment: EvidenceAssessment,
        policy_snapshot: str,
        tenant: str,
        recovery_ref: str,
    ) -> GovernanceDecision:
        descriptor = self._registry.describe(proposal.capability_ref)
        reasons: list[str] = []
        lease: AuthorityLease | None = None
        if proposal.authority_ref is None:
            reasons.append("AUTHORITY_MISSING")
        if proposal.scope_requested != descriptor.required_scope:
            reasons.append("SCOPE_MISMATCH")
        if not assessment.sufficient:
            reasons.extend(assessment.reason_codes)
        if proposal.authority_ref is not None:
            lease = self._leases.find_for_proposal(proposal)
            if lease is None:
                reasons.append("LEASE_MISSING")
            elif not lease.active:
                reasons.append("LEASE_INACTIVE")
        if reasons:
            event = self._trace.append(
                "governance_decision",
                {
                    "proposal_id": proposal.proposal_id,
                    "result": GovernanceResult.DENY.value,
                    "reasons": ",".join(sorted(set(reasons))),
                },
            )
            return GovernanceDecision(
                decision_id=f"decision://{proposal.proposal_id}",
                proposal_id=proposal.proposal_id,
                result=GovernanceResult.DENY,
                reason_codes=tuple(sorted(set(reasons))),
                scope_granted=None,
                authority_ref=proposal.authority_ref,
                lease_ref=lease.lease_ref if lease else None,
                evidence_assessment_ref=assessment.assessment_ref,
                policy_snapshot=policy_snapshot,
                validity_window=None,
                trace_ref=event.event_hash,
            )
        assert lease is not None
        now = int(time.time())
        envelope = AuthorizedActionEnvelope(
            action_id=f"action://{proposal.proposal_id}", actor=proposal.actor,
            ocs_id=proposal.ocs_id, csp_ref=proposal.csp_ref,
            object_ref=proposal.object_ref, tenant=tenant,
            context_ref=proposal.context_ref, valid_scope=proposal.scope_requested,
            authority_ref=lease.authority_ref, lease_ref=lease.lease_ref,
            policy_snapshot=policy_snapshot, evidence_refs=proposal.evidence_refs,
            evidence_assessment_ref=assessment.assessment_ref,
            idempotency_key=f"idem:{proposal.proposal_id}",
            expected_effect=proposal.expected_effect,
            side_effect_class=proposal.side_effect_class,
            reversibility_class=proposal.reversibility_class,
            recovery_ref=recovery_ref, issued_at=now, expires_at=lease.expires_at,
            max_uses=lease.max_uses, trace_id=f"trace:{proposal.proposal_id}",
        )
        event = self._trace.append(
            "governance_decision",
            {
                "proposal_id": proposal.proposal_id,
                "result": GovernanceResult.AUTHORIZE.value,
            },
        )
        return GovernanceDecision(
            decision_id=f"decision://{proposal.proposal_id}",
            proposal_id=proposal.proposal_id,
            result=GovernanceResult.AUTHORIZE,
            reason_codes=("AUTHORIZED",),
            scope_granted=proposal.scope_requested,
            authority_ref=lease.authority_ref,
            lease_ref=lease.lease_ref,
            evidence_assessment_ref=assessment.assessment_ref,
            policy_snapshot=policy_snapshot,
            validity_window=(now, lease.expires_at),
            trace_ref=event.event_hash,
            envelope=envelope,
        )
