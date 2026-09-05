from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.universal_kernel.contracts import (
    ActionProposal,
    AuthorizationDecision,
    Evidence,
    GovernanceResult,
    ReversibilityClass,
    RiskLevel,
    SideEffectClass,
)


class KernelDecisionPort(Protocol):
    def authorize(self, proposal: ActionProposal) -> GovernanceResult: ...


@dataclass(frozen=True)
class CommandKernelContext:
    lease_id: str | None
    csp_ref: str
    object_ref: str
    context_ref: str
    authority_ref: str
    policy_snapshot: str
    issued_at: float
    expires_at: float
    evidence_assessment_ref: str
    recovery_ref: str
    trace_id: str


@dataclass(frozen=True)
class CommandIntent:
    intent_id: str
    actor: str
    ocs: str
    organization: str
    capability: str
    operation: str
    scope: tuple[str, ...]
    reason: str
    expected_state_ref: str
    expected_state_version: int
    idempotency_key: str
    correlation_id: str
    causation_id: str | None
    payload: dict[str, object]
    context: CommandKernelContext
    evidence: tuple[Evidence, ...] = ()
    risk: RiskLevel = RiskLevel.LOW


@dataclass(frozen=True)
class KernelDecisionReadback:
    intent_id: str
    decision: AuthorizationDecision
    reason: str
    organization: str
    scope: tuple[str, ...]
    expected_state_ref: str
    expected_state_version: int
    idempotency_key: str
    correlation_id: str
    causation_id: str | None
    trace_id: str
    authority_ref: str
    policy_snapshot: str
    envelope_issued: bool
    executed: bool = False
    mutation_count: int = 0


class CommandKernelAdapter:
    """Read-only B4 adapter from Command intents to Kernel governance decisions.

    B4 contextualizes and asks the Universal Kernel for ALLOW/DENY/HOLD only.
    It never reserves authority, executes an effect, writes Hazel, or mutates state.
    """

    def __init__(self, kernel: KernelDecisionPort) -> None:
        self._kernel = kernel

    def decide(self, intent: CommandIntent) -> KernelDecisionReadback:
        self._validate_intent(intent)
        proposal = self._contextualize(intent)
        result = self._kernel.authorize(proposal)
        return KernelDecisionReadback(
            intent_id=intent.intent_id,
            decision=result.decision,
            reason=result.reason,
            organization=intent.organization,
            scope=intent.scope,
            expected_state_ref=intent.expected_state_ref,
            expected_state_version=intent.expected_state_version,
            idempotency_key=intent.idempotency_key,
            correlation_id=intent.correlation_id,
            causation_id=intent.causation_id,
            trace_id=intent.context.trace_id,
            authority_ref=intent.context.authority_ref,
            policy_snapshot=intent.context.policy_snapshot,
            envelope_issued=result.envelope is not None,
        )

    @staticmethod
    def _validate_intent(intent: CommandIntent) -> None:
        required = {
            "intent_id": intent.intent_id,
            "actor": intent.actor,
            "ocs": intent.ocs,
            "organization": intent.organization,
            "capability": intent.capability,
            "operation": intent.operation,
            "reason": intent.reason,
            "expected_state_ref": intent.expected_state_ref,
            "idempotency_key": intent.idempotency_key,
            "correlation_id": intent.correlation_id,
            "csp_ref": intent.context.csp_ref,
            "object_ref": intent.context.object_ref,
            "context_ref": intent.context.context_ref,
            "authority_ref": intent.context.authority_ref,
            "policy_snapshot": intent.context.policy_snapshot,
            "evidence_assessment_ref": intent.context.evidence_assessment_ref,
            "recovery_ref": intent.context.recovery_ref,
            "trace_id": intent.context.trace_id,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(f"command_intent_incomplete:{','.join(missing)}")
        if not intent.scope:
            raise ValueError("command_intent_incomplete:scope")
        if intent.expected_state_version < 0:
            raise ValueError("command_expected_state_version_invalid")

    @staticmethod
    def _contextualize(intent: CommandIntent) -> ActionProposal:
        payload = dict(intent.payload)
        payload.update(
            {
                "command_reason": intent.reason,
                "expected_state_ref": intent.expected_state_ref,
                "expected_state_version": intent.expected_state_version,
                "correlation_id": intent.correlation_id,
                "causation_id": intent.causation_id,
            }
        )
        return ActionProposal(
            action_id=intent.intent_id,
            actor=intent.actor,
            ocs=intent.ocs,
            capability=intent.capability,
            operation=intent.operation,
            payload=payload,
            risk=intent.risk,
            lease_id=intent.context.lease_id,
            evidence=intent.evidence,
            action_type="command_intent",
            issued_at=intent.context.issued_at,
            csp_ref=intent.context.csp_ref,
            object_ref=intent.context.object_ref,
            tenant=intent.organization,
            context_ref=intent.context.context_ref,
            scope=intent.scope,
            authority_ref=intent.context.authority_ref,
            policy_snapshot=intent.context.policy_snapshot,
            idempotency_key=intent.idempotency_key,
            expected_effect="none:b4-decision-only",
            side_effect_class=SideEffectClass.NONE,
            reversibility_class=ReversibilityClass.REVERSIBLE,
            recovery_ref=intent.context.recovery_ref,
            expires_at=intent.context.expires_at,
            evidence_assessment_ref=intent.context.evidence_assessment_ref,
            trace_id=intent.context.trace_id,
        )
