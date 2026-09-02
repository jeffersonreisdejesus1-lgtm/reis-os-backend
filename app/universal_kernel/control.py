from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Iterable

from .contracts import (
    ActionProposal,
    AuthorityLease,
    CapabilityDescriptor,
    ConstitutionSnapshot,
    EvidenceAssessment,
    GovernanceDecision,
    GovernanceResult,
)


class ConstitutionLoader:
    def load(self, *, constitution_ref: str, policy_version: str, prohibitions: Iterable[str], authority_ceiling: Iterable[str]) -> ConstitutionSnapshot:
        material = "|".join((constitution_ref, policy_version, *sorted(prohibitions), *sorted(authority_ceiling)))
        return ConstitutionSnapshot(constitution_ref, policy_version, tuple(prohibitions), tuple(authority_ceiling), sha256(material.encode()).hexdigest())


class CapabilityRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        self._descriptors[descriptor.capability_id] = descriptor

    def describe(self, capability_id: str) -> CapabilityDescriptor:
        return self._descriptors[capability_id]


class EvidenceEngine:
    def assess(self, assessment_id: str, *, provenance: bool = True, reliability: bool = True, freshness: bool = True, independence: bool = True, contradiction_control: bool = True, scope_fit: bool = True, auditability: bool = True) -> EvidenceAssessment:
        checks = (provenance, reliability, freshness, independence, contradiction_control, scope_fit, auditability)
        reasons = () if all(checks) else ("evidence_burden_not_satisfied",)
        return EvidenceAssessment(assessment_id, all(checks), provenance, reliability, freshness, independence, contradiction_control, scope_fit, auditability, reasons)


class AuthorityLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, AuthorityLease] = {}

    def issue(self, lease: AuthorityLease) -> None:
        if lease.transferable:
            raise ValueError("lease_must_be_non_transferable")
        self._leases[lease.lease_ref] = lease

    def validate(self, lease_ref: str, proposal: ActionProposal, now: int) -> AuthorityLease:
        lease = self._leases[lease_ref]
        if not lease.is_active(now):
            raise PermissionError("lease_inactive")
        if lease.actor != proposal.actor or lease.ocs_id != proposal.ocs_id or lease.action != proposal.action_type or lease.object_ref != proposal.object_ref or lease.context_ref != proposal.context_ref:
            raise PermissionError("lease_binding_mismatch")
        if not set(proposal.scope_requested).issubset(set(lease.scope)):
            raise PermissionError("lease_scope_mismatch")
        return lease

    def consume(self, lease_ref: str) -> None:
        lease = self._leases[lease_ref]
        if lease.revoked:
            raise PermissionError("lease_revoked")
        lease.uses += 1

    def revoke(self, lease_ref: str) -> None:
        self._leases[lease_ref].revoked = True


class GovernanceEngine:
    def decide(self, *, decision_id: str, proposal: ActionProposal, constitution: ConstitutionSnapshot, capability: CapabilityDescriptor, evidence: EvidenceAssessment, lease: AuthorityLease | None, now: int, high_risk: bool = False) -> GovernanceDecision:
        if proposal.action_type in constitution.inherited_prohibitions:
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.DENY, ("constitutional_prohibition",))
        if not set(proposal.scope_requested).issubset(set(capability.required_scope)):
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.DENY, ("capability_scope_mismatch",))
        if not set(proposal.scope_requested).issubset(set(constitution.authority_ceiling)):
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.DENY, ("ancestry_authority_ceiling",))
        if lease is None or not lease.is_active(now):
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.DENY, ("lease_invalid",))
        if high_risk and not evidence.adequate:
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.HOLD, ("high_risk_evidence_failure",), evidence_assessment_ref=evidence.assessment_id)
        if not evidence.adequate:
            return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.DENY, ("evidence_inadequate",), evidence_assessment_ref=evidence.assessment_id)
        return GovernanceDecision(decision_id, proposal.proposal_id, GovernanceResult.AUTHORIZE, (), proposal.scope_requested, f"authority:{lease.lease_ref}", lease.lease_ref, evidence.assessment_id, constitution.policy_version, (now, lease.expires_at), f"trace:{proposal.proposal_id}")
