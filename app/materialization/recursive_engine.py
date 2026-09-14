from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from app.materialization.authority import AuthorityBoundary, MutationKind


class CyclePhase(StrEnum):
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    READBACK = "readback"
    EVALUATE = "evaluate"
    TERMINATED = "terminated"
    FAILED = "failed"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


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
                 boundary: AuthorityBoundary | None = None,
                 store_path: Path | None = None) -> None:
        if max_depth < 1:
            raise ValueError("max_depth_must_be_positive")
        self._max_depth = max_depth
        self._boundary = boundary or AuthorityBoundary()
        self._seen_missions: dict[str, str] = {}
        self._store_path = Path(store_path) if store_path else None
        if self._store_path:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._store_path) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS recursive_runs "
                    "(replay_key TEXT PRIMARY KEY, status TEXT NOT NULL)"
                )

    @staticmethod
    def _state_hash(state: str) -> str:
        return sha256(state.encode()).hexdigest()

    def _status(self, key: str) -> str | None:
        if self._store_path:
            with sqlite3.connect(self._store_path) as conn:
                row = conn.execute(
                    "SELECT status FROM recursive_runs WHERE replay_key=?", (key,)
                ).fetchone()
                return row[0] if row else None
        return self._seen_missions.get(key)

    def _set(self, key: str, status: str) -> None:
        if self._store_path:
            with sqlite3.connect(self._store_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO recursive_runs(replay_key, status) VALUES (?,?)",
                    (key, status),
                )
            return
        self._seen_missions[key] = status

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
        prior = self._status(replay_key)
        if prior == RunStatus.COMPLETED:
            return RecursiveReceipt(
                mission_id=mission_id,
                terminated=True,
                termination_reason="replay_blocked",
                authority_gained=False,
                replayed=True,
            )
        if prior == RunStatus.RUNNING:
            return RecursiveReceipt(
                mission_id=mission_id,
                terminated=False,
                termination_reason="run_interrupted",
                failure="run_interrupted",
                authority_gained=False,
                replayed=False,
            )
        if prior == RunStatus.FAILED:
            return RecursiveReceipt(
                mission_id=mission_id,
                terminated=True,
                termination_reason="prior_failed",
                failure="prior_failed",
                authority_gained=False,
                replayed=True,
            )
        self._set(replay_key, RunStatus.RUNNING)

        state = initial_state
        seen_states: set[str] = {state}
        records: list[IterationRecord] = []
        transformer = step or (lambda current, index: f"{current}|nudge:{index}")

        def finish(receipt: RecursiveReceipt, ok: bool) -> RecursiveReceipt:
            self._set(replay_key, RunStatus.COMPLETED if ok else RunStatus.FAILED)
            return receipt

        for index in range(1, self._max_depth + 1):
            executed = transformer(state, index)
            if executed is None:
                return finish(RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="invalid_state",
                    failure="invalid_state",
                    authority_gained=False,
                ), False)
            digest = self._state_hash(executed)
            if executed in seen_states:
                records.append(IterationRecord(index, CyclePhase.FAILED, executed, digest, executed, "cycle"))
                return finish(RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="cycle_detected",
                    failure="cycle_detected",
                    authority_gained=False,
                ), False)
            seen_states.add(executed)
            reached = goal in executed or executed == goal
            phase = CyclePhase.TERMINATED if reached or index == self._max_depth else CyclePhase.EVALUATE
            records.append(
                IterationRecord(index, phase, state, digest, executed, "stop" if reached else "continue")
            )
            if reached:
                return finish(RecursiveReceipt(
                    mission_id=mission_id,
                    iterations=records,
                    terminated=True,
                    termination_reason="goal_met",
                    authority_gained=False,
                ), True)
            state = executed
        return finish(RecursiveReceipt(
            mission_id=mission_id,
            iterations=records,
            terminated=True,
            termination_reason="budget_exhausted",
            authority_gained=False,
        ), True)
