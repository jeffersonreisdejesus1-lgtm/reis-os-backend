from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence

from .operational_learning_loop import ClosedOperationalLearningResult


class RealMissionQualificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MissionQualificationEvidence:
    mission_id: str
    mission_class: str
    mission_input: str
    cognitive_entry_receipt: str
    capability_discovery_receipt: str
    ocs_composition_receipt: str
    authority_receipt: str
    governed_execution_receipt: str
    evidence_receipt: str
    state_hash: str
    learning_receipt: str
    final_status: str
    real_effect_observed: bool


@dataclass(frozen=True, slots=True)
class RealMissionQualificationResult:
    evidence: MissionQualificationEvidence
    route_changed_after_failure: bool
    qualification_receipt: str


class RealMissionQualifier:
    """COI13: qualify a materially evidenced institutional mission across COI1-COI12."""

    _MISSION_CLASSES = frozenset({
        "SOFTWARE_ENGINEERING",
        "INSTITUTIONAL_RESEARCH_PROVENANCE",
        "ANDROID_OPERATION",
        "FAILURE_RECOVERY_REPLAN",
        "AUTHORITY_DENIED",
    })
    _FINAL_STATUSES = frozenset({"SUCCESS", "DENIED_AS_DESIGNED"})

    def qualify(
        self,
        *,
        evidence: MissionQualificationEvidence,
        learning: ClosedOperationalLearningResult | None = None,
    ) -> RealMissionQualificationResult:
        self._validate_evidence(evidence)

        route_changed = False
        if evidence.mission_class == "FAILURE_RECOVERY_REPLAN":
            if learning is None:
                raise RealMissionQualificationError("coi13_learning_result_required")
            if learning.feedback.mission_id != evidence.mission_id:
                raise RealMissionQualificationError("coi13_learning_mission_mismatch")
            if learning.learning_receipt != evidence.learning_receipt:
                raise RealMissionQualificationError("coi13_learning_receipt_mismatch")
            if learning.feedback.outcome not in {"FAILURE", "PARTIAL"}:
                raise RealMissionQualificationError("coi13_failure_feedback_required")
            if not learning.route_changed:
                raise RealMissionQualificationError("coi13_different_route_required")
            if learning.next_plan.selected_capability_id == learning.previous_plan.selected_capability_id:
                raise RealMissionQualificationError("coi13_route_change_not_material")
            route_changed = True

        receipt = self._digest({
            "mission_id": evidence.mission_id,
            "mission_class": evidence.mission_class,
            "mission_input": evidence.mission_input,
            "cognitive_entry_receipt": evidence.cognitive_entry_receipt,
            "capability_discovery_receipt": evidence.capability_discovery_receipt,
            "ocs_composition_receipt": evidence.ocs_composition_receipt,
            "authority_receipt": evidence.authority_receipt,
            "governed_execution_receipt": evidence.governed_execution_receipt,
            "evidence_receipt": evidence.evidence_receipt,
            "state_hash": evidence.state_hash,
            "learning_receipt": evidence.learning_receipt,
            "final_status": evidence.final_status,
            "real_effect_observed": evidence.real_effect_observed,
            "route_changed_after_failure": route_changed,
        })
        return RealMissionQualificationResult(evidence, route_changed, receipt)

    def qualify_suite(
        self,
        missions: Sequence[RealMissionQualificationResult],
    ) -> str:
        if not missions:
            raise RealMissionQualificationError("coi13_missions_required")
        mission_ids = [item.evidence.mission_id for item in missions]
        if len(set(mission_ids)) != len(mission_ids):
            raise RealMissionQualificationError("coi13_duplicate_mission")
        classes = {item.evidence.mission_class for item in missions}
        if "FAILURE_RECOVERY_REPLAN" not in classes:
            raise RealMissionQualificationError("coi13_failure_recovery_mission_required")
        if not any(item.route_changed_after_failure for item in missions):
            raise RealMissionQualificationError("coi13_observed_replan_required")
        return self._digest({
            "mission_ids": sorted(mission_ids),
            "qualification_receipts": sorted(item.qualification_receipt for item in missions),
            "mission_classes": sorted(classes),
        })

    def _validate_evidence(self, evidence: MissionQualificationEvidence) -> None:
        if evidence.mission_class not in self._MISSION_CLASSES:
            raise RealMissionQualificationError("coi13_mission_class_invalid")
        if evidence.final_status not in self._FINAL_STATUSES:
            raise RealMissionQualificationError("coi13_final_status_unqualified")
        required = (
            evidence.mission_id,
            evidence.mission_input,
            evidence.cognitive_entry_receipt,
            evidence.capability_discovery_receipt,
            evidence.ocs_composition_receipt,
            evidence.authority_receipt,
            evidence.governed_execution_receipt,
            evidence.evidence_receipt,
            evidence.state_hash,
            evidence.learning_receipt,
        )
        if any(not isinstance(value, str) or not value.strip() for value in required):
            raise RealMissionQualificationError("coi13_evidence_chain_incomplete")
        if evidence.final_status == "SUCCESS" and not evidence.real_effect_observed:
            raise RealMissionQualificationError("coi13_success_requires_observed_effect")
        if evidence.mission_class == "AUTHORITY_DENIED" and evidence.final_status != "DENIED_AS_DESIGNED":
            raise RealMissionQualificationError("coi13_authority_denial_status_required")

    @staticmethod
    def _digest(payload: Mapping[str, object]) -> str:
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()
