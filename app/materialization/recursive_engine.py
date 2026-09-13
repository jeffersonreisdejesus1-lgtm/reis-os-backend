from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

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


class RecursiveEngine:
    """STATE→ANALYZE→PLAN→EXECUTE→READBACK→EVALUATE with hard depth."""

    def __init__(self, *,
                 max_depth: int = 4,
                 boundary: AuthorityBoundary | None = None) -> None:
        if max_depth < 1:
            raise ValueError("max_depth_must_be_positive")
        self._max_depth = max_depth
        self._boundary = boundary or AuthorityBoundary()

    def run(self, *,
            actor: str,
            mission_id: str,
            initial_state: str,
            goal: str) -> RecursiveReceipt:
        allowed = self._boundary.decide(actor=actor, kind=MutationKind.RUN_TEST)
        if not allowed.allowed:
            return RecursiveReceipt(
                mission_id=mission_id,
                failure=allowed.reason,
                termination_reason="authority_denied",
            )
        state = initial_state
        records: list[IterationRecord] = []
        for index in range(1, self._max_depth + 1):
            analysis = f"gap:{goal}!={state}"
            plan = f"nudge:{index}"
            executed = f"{state}|{plan}"
            readback = executed
            if goal in readback or index == self._max_depth:
                records.append(
                    IterationRecord(index, CyclePhase.TERMINATED, state, readback, "stop")
                )
                return RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="goal_or_budget",
                    authority_gained=False,
                )
            records.append(
                IterationRecord(index, CyclePhase.EVALUATE, state, readback, analysis)
            )
            state = executed
        return RecursiveReceipt(
            mission_id=mission_id,
            iterations=records,
            terminated=True,
            termination_reason="budget_exhausted",
            authority_gained=False,
        )
