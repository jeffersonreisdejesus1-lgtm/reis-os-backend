from __future__ import annotations

from itertools import count

from .contracts import (
    ActionProposal,
    AuthorizationDecision,
    ExecutionResult,
    StateRecord,
)
from .effect_recovery import ThinEffector
from .governance import GovernanceEngine
from .state_trace import StateCore, TraceCore


class UniversalKernelRuntime:
    def __init__(
        self,
        governance: GovernanceEngine,
        effector: ThinEffector,
        state: StateCore,
        trace: TraceCore,
    ) -> None:
        self._governance = governance
        self._effector = effector
        self._state = state
        self._trace = trace
        self._seq = count(1)
        self._completed: dict[str, tuple[str, ExecutionResult]] = {}

    def execute(self, proposal: ActionProposal) -> ExecutionResult:
        if proposal.idempotency_key is not None:
            completed = self._completed.get(proposal.idempotency_key)
            if completed is not None:
                completed_action_id, completed_result = completed
                if completed_action_id != proposal.action_id:
                    return ExecutionResult(False, False, True, "idempotency_conflict")
                return completed_result

        governance = self._governance.authorize(proposal)
        if (
            governance.decision is AuthorizationDecision.DENY
            or governance.envelope is None
        ):
            return ExecutionResult(False, False, True, governance.reason)

        reservation = self._governance.reserve_authority(governance.envelope)
        if (
            reservation.decision is AuthorizationDecision.DENY
            or reservation.envelope is None
        ):
            return ExecutionResult(False, False, True, reservation.reason)

        envelope = reservation.envelope
        effected = False
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
            self._state.write(state, lambda stored: stored == state)
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "state"),
                action_id=proposal.action_id,
                stage="STATE_MANAGER_COMMIT",
                details={"state_id": state.state_id, "version": state.version},
            )
        except RuntimeError as exc:
            return ExecutionResult(True, effected, False, str(exc))

        result = ExecutionResult(True, True, True, "effect_proven", readback)
        self._completed[envelope.idempotency_key] = (envelope.action_id, result)
        return result

    def _event_id(self, action_id: str, stage: str) -> str:
        return f"trace:{action_id}:{stage}:{next(self._seq)}"
