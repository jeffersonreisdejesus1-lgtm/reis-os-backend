from __future__ import annotations

from dataclasses import dataclass

from .contracts import ActionProposal, AuthorizedActionEnvelope, GovernanceResult
from .control import AuthorityLeaseManager, CapabilityRegistry, EvidenceEngine, GovernanceEngine
from .material import ThinEffector, ToolBroker
from .state_trace import StateCore, TraceCore


@dataclass
class UniversalKernel:
    capabilities: CapabilityRegistry
    evidence: EvidenceEngine
    leases: AuthorityLeaseManager
    governance: GovernanceEngine
    broker: ToolBroker
    effector: ThinEffector
    state: StateCore
    trace: TraceCore

    def execute(self, *, proposal: ActionProposal, constitution, lease_ref: str, assessment_id: str, adapter_id: str, tenant: str, recovery_ref: str, idempotency_key: str, now: int, high_risk: bool = False):
        capability = self.capabilities.describe(proposal.capability_ref)
        assessment = self.evidence.assess(assessment_id)
        try:
            lease = self.leases.validate(lease_ref, proposal, now)
        except (KeyError, PermissionError):
            lease = None
        decision = self.governance.decide(
            decision_id=f"decision:{proposal.proposal_id}",
            proposal=proposal,
            constitution=constitution,
            capability=capability,
            evidence=assessment,
            lease=lease,
            now=now,
            high_risk=high_risk,
        )
        self.trace.append(event_id=f"decision:{proposal.proposal_id}", trace_id=f"trace:{proposal.proposal_id}", event_type="authorization" if decision.result is GovernanceResult.AUTHORIZE else "deny", producer_kind="governance", ocs_id=proposal.ocs_id, payload={"result": decision.result.value})
        envelope = None
        if decision.result is GovernanceResult.AUTHORIZE and lease is not None:
            envelope = AuthorizedActionEnvelope(
                action_id=f"action:{proposal.proposal_id}", actor=proposal.actor, ocs_id=proposal.ocs_id, csp_ref=proposal.csp_ref,
                object_ref=proposal.object_ref, tenant=tenant, context_ref=proposal.context_ref, valid_scope=decision.scope_granted,
                authority_ref=decision.authority_ref or "", lease_ref=lease.lease_ref, policy_snapshot=decision.policy_snapshot or "",
                evidence_refs=proposal.evidence_refs, evidence_assessment_ref=assessment.assessment_id, idempotency_key=idempotency_key,
                expected_effect=proposal.expected_effect, side_effect_class=proposal.side_effect_class,
                reversibility_class=proposal.reversibility_class, recovery_ref=recovery_ref, issued_at=now, expires_at=lease.expires_at,
                max_uses=lease.max_uses, trace_id=f"trace:{proposal.proposal_id}")
        result = self.broker.resolve_and_execute(decision=decision, envelope=envelope, adapter_id=adapter_id, effector=self.effector, now=now)
        if result.attempted and lease is not None:
            self.leases.consume(lease.lease_ref)
            self.trace.append(event_id=f"tool:{proposal.proposal_id}", trace_id=envelope.trace_id, event_type="tool_result", producer_kind="thin_effector", ocs_id=proposal.ocs_id, predecessors=(f"decision:{proposal.proposal_id}",), payload={"mutation_count": result.mutation_count, "readback_ref": result.readback_ref})
        return decision, result
