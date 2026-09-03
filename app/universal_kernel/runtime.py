from __future__ import annotations

from itertools import count

from .contracts import (
    ActionProposal,
    AuthorizationDecision,
    ExecutionResult,
    GovernanceResult,
    StateRecord,
)
from .effect_recovery import (
    MaterialEffectFailure,
    RecoveryManager,
    ThinEffector,
)
from .governance import GovernanceEngine
from .state_trace import StateCore, TraceCore


class UniversalKernelRuntime:
    def __init__(
        self,
        governance: GovernanceEngine,
        effector: ThinEffector,
        state: StateCore,
        trace: TraceCore,
        recovery: RecoveryManager | None = None,
    ) -> None:
        self._governance = governance
        self._effector = effector
        self._state = state
        self._trace = trace
        self._recovery = recovery
        self._seq = count(1)
        self._completed: dict[str, tuple[str, ExecutionResult]] = {}

    def execute(self, proposal: ActionProposal) -> ExecutionResult:
        if proposal.idempotency_key is not None:
            completed = self._completed.get(proposal.idempotency_key)
            if completed is not None:
                completed_action_id, completed_result = completed
                if completed_action_id != proposal.action_id:
                    return ExecutionResult(
                        False,
                        False,
                        True,
                        "idempotency_conflict",
                        governance_decision=AuthorizationDecision.DENY,
                        trace_id=proposal.trace_id,
                    )
                return completed_result

        governance = self._governance.authorize(proposal)
        if governance.decision is not AuthorizationDecision.ALLOW:
            trace_ok = self._trace_governance(proposal, governance)
            return ExecutionResult(
                False,
                False,
                trace_ok,
                governance.reason,
                governance_decision=governance.decision,
                trace_id=proposal.trace_id,
            )
        if governance.envelope is None:
            return ExecutionResult(
                False,
                False,
                False,
                "authorized_envelope_missing",
                governance_decision=governance.decision,
                trace_id=proposal.trace_id,
            )

        # A preflight fault must not spend authority or reach the broker.
        try:
            self._trace.preflight_gate()
        except RuntimeError as exc:
            return ExecutionResult(
                True,
                False,
                False,
                str(exc),
                governance_decision=governance.decision,
                trace_id=proposal.trace_id,
            )

        reservation = self._governance.reserve_authority(governance.envelope)
        if (
            reservation.decision is AuthorizationDecision.DENY
            or reservation.envelope is None
        ):
            return ExecutionResult(
                False,
                False,
                True,
                reservation.reason,
                governance_decision=AuthorizationDecision.DENY,
                trace_id=proposal.trace_id,
            )

        trace_ok = self._trace_governance(proposal, governance)
        if not trace_ok:
            return ExecutionResult(
                True,
                False,
                False,
                "trace_append_failed",
                governance_decision=governance.decision,
                trace_id=proposal.trace_id,
            )

        envelope = reservation.envelope
        effected = False
        readback = None
        try:
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "authorized"),
                action_id=proposal.action_id,
                stage="AUTHORIZED_ACTION_ENVELOPE",
                details={
                    "trace_id": envelope.trace_id,
                    "lease_id": envelope.lease_id,
                    "lease_use_index": envelope.lease_use_index,
                    "idempotency_key": envelope.idempotency_key,
                },
            )
            self._trace.preflight(
                event_id=self._event_id(proposal.action_id, "preflight"),
                action_id=proposal.action_id,
                trace_id=envelope.trace_id,
                authority_ref=envelope.authority_ref,
                lease_id=envelope.lease_id,
            )
            readback = self._effector.execute(envelope)
            effected = True
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "readback"),
                action_id=proposal.action_id,
                stage="MATERIAL_EFFECT_READBACK",
                details={"mutation_id": readback.mutation_id},
            )
            current = self._state.current(proposal.ocs)
            state = StateRecord(
                state_id=f"state:{proposal.ocs}:{next(self._seq)}",
                ocs=proposal.ocs,
                version=1 if current is None else current.version + 1,
                predecessor=None if current is None else current.state_id,
                payload=readback.state,
                verified=True,
            )
            self._state.write(
                state,
                lambda stored: stored == state,
                actor_ocs_id=proposal.ocs,
                target_namespace=f"state://{proposal.ocs}/runtime",
                state_ref=state.state_id,
                authority_context=envelope.authority_ref,
            )
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "state"),
                action_id=proposal.action_id,
                stage="STATE_MANAGER_COMMIT",
                details={"state_id": state.state_id, "version": state.version},
            )
            lease_state = self._governance.finalize_authority(envelope)
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "lease-finalize"),
                action_id=proposal.action_id,
                stage="LEASE_FINALIZE_OR_RELEASE",
                details={
                    "lease_id": envelope.lease_id,
                    "lease_state": lease_state.value,
                },
            )
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "close"),
                action_id=proposal.action_id,
                stage="TRACE_CLOSE",
                details={"trace_id": envelope.trace_id},
            )
        except MaterialEffectFailure as exc:
            effected = True
            recovery_receipt = None
            if self._recovery is not None:
                recovery_receipt = self._recovery.recover_post_effect(
                    envelope,
                    exc.mutation_id,
                    self._effector,
                )
            return ExecutionResult(
                True,
                True,
                False,
                str(exc),
                governance_decision=AuthorizationDecision.ALLOW,
                trace_id=envelope.trace_id,
                recovery_receipt=recovery_receipt,
                residual_effect=(
                    True
                    if recovery_receipt is None
                    else recovery_receipt.residual_effect
                ),
            )
        except RuntimeError as exc:
            reason = str(exc)
            residual_effect = effected
            return ExecutionResult(
                True,
                effected,
                False,
                reason,
                readback=readback,
                governance_decision=AuthorizationDecision.ALLOW,
                trace_id=envelope.trace_id,
                residual_effect=residual_effect,
            )

        result = ExecutionResult(
            True,
            True,
            True,
            "effect_proven",
            readback,
            governance_decision=AuthorizationDecision.ALLOW,
            trace_id=envelope.trace_id,
        )
        self._completed[envelope.idempotency_key] = (envelope.action_id, result)
        return result

    def _trace_governance(
        self,
        proposal: ActionProposal,
        governance: GovernanceResult,
    ) -> bool:
        assessment = governance.evidence_assessment
        try:
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "proposal"),
                action_id=proposal.action_id,
                stage="ACTION_PROPOSAL",
                details={"trace_id": proposal.trace_id or ""},
            )
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "evidence"),
                action_id=proposal.action_id,
                stage="EVIDENCE_ASSESSMENT",
                details={
                    "sufficiency": (
                        None if assessment is None else assessment.sufficiency
                    ),
                    "deficits": () if assessment is None else assessment.deficits,
                },
            )
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "governance"),
                action_id=proposal.action_id,
                stage="GOVERNANCE_DECISION",
                details={
                    "decision": governance.decision.value,
                    "reason": governance.reason,
                    "trace_id": proposal.trace_id or "",
                },
            )
        except RuntimeError:
            return False
        return True

    def _event_id(self, action_id: str, stage: str) -> str:
        return f"trace:{action_id}:{stage}:{next(self._seq)}"
