from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .observation_evidence_state import ObservationEvidenceStateResult
from .operational_learning_loop import (
    ClosedOperationalLearningLoop,
    ClosedOperationalLearningResult,
    LearningFeedback,
    OperationalPlan,
)


class PersistentOperationalLearningError(RuntimeError):
    pass


class PersistentOperationalLearningStore:
    """Durable COI12 learning state backed by SQLite.

    The store is intentionally narrow: it persists the qualified next plan,
    its feedback, and the learning receipt. Reopening the database establishes
    a process/runtime boundary without relying on in-memory object identity.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = str(db_path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operational_learning_state (
                mission_id TEXT PRIMARY KEY,
                plan_json TEXT NOT NULL,
                feedback_json TEXT NOT NULL,
                learning_receipt TEXT NOT NULL,
                committed_state_hash TEXT NOT NULL,
                state_version INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def commit(self, result: ClosedOperationalLearningResult) -> None:
        plan = result.next_plan
        feedback = result.feedback
        if plan.mission_id != feedback.mission_id:
            raise PersistentOperationalLearningError("persistent_learning_mission_mismatch")
        if plan.state_hash != feedback.state_hash:
            raise PersistentOperationalLearningError("persistent_learning_state_hash_mismatch")
        if not result.learning_receipt.strip():
            raise PersistentOperationalLearningError("persistent_learning_receipt_required")
        if plan.feedback_receipt is None:
            raise PersistentOperationalLearningError("persistent_learning_feedback_receipt_required")

        with self._conn:
            current = self._conn.execute(
                "SELECT plan_json FROM operational_learning_state WHERE mission_id = ?",
                (plan.mission_id,),
            ).fetchone()
            if current is not None:
                prior = self._plan_from_json(current[0])
                if plan.plan_revision <= prior.plan_revision:
                    raise PersistentOperationalLearningError("persistent_learning_revision_not_monotonic")
                if plan.prior_plan_receipt != prior.plan_receipt:
                    raise PersistentOperationalLearningError("persistent_learning_lineage_mismatch")

            self._conn.execute(
                """
                INSERT INTO operational_learning_state (
                    mission_id, plan_json, feedback_json, learning_receipt,
                    committed_state_hash, state_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    plan_json = excluded.plan_json,
                    feedback_json = excluded.feedback_json,
                    learning_receipt = excluded.learning_receipt,
                    committed_state_hash = excluded.committed_state_hash,
                    state_version = excluded.state_version
                """,
                (
                    plan.mission_id,
                    self._json(asdict(plan)),
                    self._json(asdict(feedback)),
                    result.learning_receipt,
                    feedback.state_hash,
                    feedback.state_version,
                ),
            )

    def load_current_plan(self, mission_id: str) -> OperationalPlan:
        row = self._conn.execute(
            "SELECT plan_json FROM operational_learning_state WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        if row is None:
            raise PersistentOperationalLearningError("persistent_learning_state_not_found")
        return self._plan_from_json(row[0])

    def load_feedback(self, mission_id: str) -> LearningFeedback:
        row = self._conn.execute(
            "SELECT feedback_json FROM operational_learning_state WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        if row is None:
            raise PersistentOperationalLearningError("persistent_learning_state_not_found")
        data = json.loads(row[0])
        return LearningFeedback(**data)

    def load_learning_receipt(self, mission_id: str) -> str:
        row = self._conn.execute(
            "SELECT learning_receipt FROM operational_learning_state WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        if row is None:
            raise PersistentOperationalLearningError("persistent_learning_state_not_found")
        return str(row[0])

    @staticmethod
    def _json(payload: object) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _plan_from_json(payload: str) -> OperationalPlan:
        return OperationalPlan(**json.loads(payload))


class PersistentClosedOperationalLearningRuntime:
    """COI15 remediation runtime for mission N -> persisted learning -> mission N+1.

    New mission execution resumes only through `resume_for_next_mission`, which
    loads the committed plan from durable state and validates the learning
    receipt expected by the caller. This prevents silently falling back to a
    stale in-memory plan after a runtime restart.
    """

    def __init__(
        self,
        *,
        store: PersistentOperationalLearningStore,
        loop: ClosedOperationalLearningLoop | None = None,
    ) -> None:
        self._store = store
        self._loop = loop or ClosedOperationalLearningLoop()

    def close_loop_and_commit(
        self,
        *,
        previous_plan: OperationalPlan,
        coi11_result: ObservationEvidenceStateResult,
        candidate_capabilities: Sequence[str],
        outcome: str,
    ) -> ClosedOperationalLearningResult:
        result = self._loop.close_loop(
            previous_plan=previous_plan,
            coi11_result=coi11_result,
            candidate_capabilities=candidate_capabilities,
            outcome=outcome,
        )
        self._store.commit(result)
        return result

    def resume_for_next_mission(
        self,
        *,
        mission_id: str,
        expected_learning_receipt: str,
    ) -> OperationalPlan:
        if not mission_id.strip() or not expected_learning_receipt.strip():
            raise PersistentOperationalLearningError("persistent_learning_resume_context_required")
        actual_receipt = self._store.load_learning_receipt(mission_id)
        if actual_receipt != expected_learning_receipt:
            raise PersistentOperationalLearningError("persistent_learning_receipt_mismatch")
        plan = self._store.load_current_plan(mission_id)
        feedback = self._store.load_feedback(mission_id)
        if plan.state_hash != feedback.state_hash:
            raise PersistentOperationalLearningError("persistent_learning_state_hash_mismatch")
        if plan.plan_revision < 2:
            raise PersistentOperationalLearningError("persistent_learning_unadvanced_plan")
        if plan.feedback_receipt is None:
            raise PersistentOperationalLearningError("persistent_learning_feedback_receipt_required")
        return plan
