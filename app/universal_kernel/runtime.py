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

    def execute(self, proposal: ActionProposal) -> ExecutionResult:
        governance = self._governance.authorize(proposal)
        if governance.decision is AuthorizationDecision.DENY or governance.envelope is None:
            return ExecutionResult(False, False, True, governance.reason)
        envelope = governance.envelope
        try:
            self._trace.append_stage(
                event_id=self._event_id(proposal.action_id, "authorized"),
                action_id=proposal.action_id,
                stage="AUTHORIZED_ACTION_ENVELOPE",
            )
            readback = self._effector.execute(envelope)
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
            return ExecutionResult(True, True, False, str(exc))
        return ExecutionResult(True, True, True, "effect_proven", readback)

    def _event_id(self, action_id: str, stage: str) -> str:
        return f"trace:{action_id}:{stage}:{next(self._seq)}"
