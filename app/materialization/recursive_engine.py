from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256

from app.materialization.authority import AuthorityBoundary, MutationKind


class CyclePhase(StrEnum):
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    READBACK = "readback"
    EVALUATE = "evaluate"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class IterationRecord:
    index: int
    phase: CyclePhase
    state: str
    state_hash: str
    readback: str
    next_action: str


@dataclass
class RecursiveReceipt:
    mission_id: str
    iterations: list[IterationRecord] = field(default_factory=list)
    terminated: bool = False
    termination_reason: str = ""
    authority_gained: bool = False
    failure: str | None = None
    replayed: bool = False


class RecursiveEngine:
    def __init__(self, *,
                 max_depth: int = 4,
                 boundary: AuthorityBoundary | None = None) -> None:
        if max_depth < 1:
            raise ValueError("max_depth_must_be_positive")
        self._max_depth = max_depth
        self._boundary = boundary or AuthorityBoundary()
        self._seen_missions: set[str] = set()

    @staticmethod
    def _state_hash(state: str) -> str:
        return sha256(state.encode()).hexdigest()

    def run(self, *,
            actor: str,
            mission_id: str,
            initial_state: str,
            goal: str,
            step=None) -> RecursiveReceipt:
        allowed = self._boundary.decide(actor=actor, kind=MutationKind.RUN_TEST)
        if not allowed.allowed:
            return RecursiveReceipt(
                mission_id=mission_id,
                failure=allowed.reason,
                termination_reason="authority_denied",
            )
        replay_key = f"{mission_id}:{initial_state}:{goal}"
        if replay_key in self._seen_missions:
            return RecursiveReceipt(
                mission_id=mission_id,
                terminated=True,
                termination_reason="replay_blocked",
                authority_gained=False,
                replayed=True,
            )
        self._seen_missions.add(replay_key)

        state = initial_state
        seen_states: set[str] = {state}
        records: list[IterationRecord] = []
        transformer = step or (lambda current, index: f"{current}|nudge:{index}")

        for index in range(1, self._max_depth + 1):
            executed = transformer(state, index)
            if executed is None:
                return RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="invalid_state",
                    failure="invalid_state",
                    authority_gained=False,
                )
            digest = self._state_hash(executed)
            if executed in seen_states:
                records.append(
                    IterationRecord(
                        index, CyclePhase.FAILED, executed, digest, executed, "cycle"
                    )
                )
                return RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="cycle_detected",
                    failure="cycle_detected",
                    authority_gained=False,
                )
            seen_states.add(executed)
            reached = goal in executed or executed == goal
            phase = CyclePhase.TERMINATED if reached or index == self._max_depth else CyclePhase.EVALUATE
            records.append(
                IterationRecord(index, phase, state, digest, executed, "stop" if reached else "continue")
            )
            if reached:
                return RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="goal_met",
                    authority_gained=False,
                )
            state = executed
        return RecursiveReceipt(
            mission_id=mission_id,
            iterations=records,
            terminated=True,
            termination_reason="budget_exhausted",
            authority_gained=False,
        )
