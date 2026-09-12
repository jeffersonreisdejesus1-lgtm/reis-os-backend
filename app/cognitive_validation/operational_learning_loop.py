from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence

from .observation_evidence_state import ObservationEvidenceStateResult


class OperationalLearningLoopError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LearningFeedback:
    mission_id: str
    evidence_receipt: str
    state_hash: str
    state_version: int
    outcome: str
    failed_capability_id: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalPlan:
    mission_id: str
    plan_revision: int
    selected_capability_id: str
    prior_plan_receipt: str | None
    feedback_receipt: str | None
    state_hash: str
    plan_receipt: str


@dataclass(frozen=True, slots=True)
class ClosedOperationalLearningResult:
    feedback: LearningFeedback
    previous_plan: OperationalPlan
    next_plan: OperationalPlan
    route_changed: bool
    learning_receipt: str


class ClosedOperationalLearningLoop:
    """COI12: make qualified COI11 feedback causally change the next operational decision."""

    _OUTCOMES = frozenset({"SUCCESS", "FAILURE", "PARTIAL"})

    def close_loop(
        self,
        *,
        previous_plan: OperationalPlan,
        coi11_result: ObservationEvidenceStateResult,
        candidate_capabilities: Sequence[str],
        outcome: str,
    ) -> ClosedOperationalLearningResult:
        if outcome not in self._OUTCOMES:
            raise OperationalLearningLoopError("learning_outcome_invalid")
        if not candidate_capabilities or any(not isinstance(item, str) or not item.strip() for item in candidate_capabilities):
            raise OperationalLearningLoopError("learning_candidates_required")
        if len(set(candidate_capabilities)) != len(candidate_capabilities):
            raise OperationalLearningLoopError("learning_duplicate_candidate")

        evidence = coi11_result.evidence
        state = coi11_result.state_snapshot
        if previous_plan.mission_id != evidence.mission_id or state.mission_id != evidence.mission_id:
            raise OperationalLearningLoopError("learning_mission_mismatch")
        if state.evidence_receipt != evidence.evidence_receipt:
            raise OperationalLearningLoopError("learning_evidence_state_mismatch")
        if previous_plan.state_hash == state.state_hash:
            raise OperationalLearningLoopError("learning_requires_new_state")
        if previous_plan.selected_capability_id not in candidate_capabilities:
            raise OperationalLearningLoopError("learning_previous_route_not_candidate")

        failed_capability = previous_plan.selected_capability_id if outcome in {"FAILURE", "PARTIAL"} else None
        feedback = LearningFeedback(
            mission_id=evidence.mission_id,
            evidence_receipt=evidence.evidence_receipt,
            state_hash=state.state_hash,
            state_version=state.state_version,
            outcome=outcome,
            failed_capability_id=failed_capability,
        )
        feedback_receipt = self._digest({
            "mission_id": feedback.mission_id,
            "evidence_receipt": feedback.evidence_receipt,
            "state_hash": feedback.state_hash,
            "state_version": feedback.state_version,
            "outcome": feedback.outcome,
            "failed_capability_id": feedback.failed_capability_id,
        })

        next_capability = previous_plan.selected_capability_id
        if failed_capability is not None:
            alternatives = sorted(item for item in candidate_capabilities if item != failed_capability)
            if not alternatives:
                raise OperationalLearningLoopError("learning_no_alternative_route")
            next_capability = alternatives[0]

        next_plan = OperationalPlan(
            mission_id=previous_plan.mission_id,
            plan_revision=previous_plan.plan_revision + 1,
            selected_capability_id=next_capability,
            prior_plan_receipt=previous_plan.plan_receipt,
            feedback_receipt=feedback_receipt,
            state_hash=state.state_hash,
            plan_receipt=self._digest({
                "mission_id": previous_plan.mission_id,
                "plan_revision": previous_plan.plan_revision + 1,
                "selected_capability_id": next_capability,
                "prior_plan_receipt": previous_plan.plan_receipt,
                "feedback_receipt": feedback_receipt,
                "state_hash": state.state_hash,
            }),
        )
        route_changed = next_capability != previous_plan.selected_capability_id
        learning_receipt = self._digest({
            "previous_plan_receipt": previous_plan.plan_receipt,
            "feedback_receipt": feedback_receipt,
            "next_plan_receipt": next_plan.plan_receipt,
            "route_changed": route_changed,
        })
        return ClosedOperationalLearningResult(feedback, previous_plan, next_plan, route_changed, learning_receipt)

    @staticmethod
    def initial_plan(*, mission_id: str, capability_id: str, state_hash: str = "GENESIS") -> OperationalPlan:
        for value in (mission_id, capability_id, state_hash):
            if not isinstance(value, str) or not value.strip():
                raise OperationalLearningLoopError("learning_initial_plan_field_required")
        receipt = ClosedOperationalLearningLoop._digest({
            "mission_id": mission_id,
            "plan_revision": 1,
            "selected_capability_id": capability_id,
            "state_hash": state_hash,
        })
        return OperationalPlan(mission_id, 1, capability_id, None, None, state_hash, receipt)

    @staticmethod
    def _digest(payload: Mapping[str, object]) -> str:
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()
