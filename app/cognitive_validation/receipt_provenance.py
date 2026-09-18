from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from .action_receipt import ActionCognitiveReceipt, ActionCognitiveReceiptIssuer
from .authority_aware_discovery import AuthorityAwareCapabilityDiscovery, AuthorityReceipt
from .mission_receipt import MissionCognitiveReceipt, MissionCognitiveReceiptIssuer
from .observation_evidence_state import ObservationEvidenceStateResult
from .operational_learning_loop import ClosedOperationalLearningResult
from .governed_execution import GovernedSoftwareExecutionResult


class ReceiptProvenanceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReceiptProvenanceResult:
    mission_id: str
    mission_receipt_id: str
    action_receipt_id: str
    authority_receipt_id: str
    governed_execution_receipt: str
    evidence_receipt: str
    state_hash: str
    learning_receipt: str
    lineage_receipt: str


class ReceiptProvenanceVerifier:
    """Independent COI15 remediation verifier for COI3->COI12 receipt lineage.

    Trusted issuer/verifier objects are injected; strings alone never qualify.
    The verifier checks cryptographic issuer authenticity where those receipts are
    signed, exact mission/context lineage, and deterministic downstream receipts.
    Post-execution provenance validates the immutable signed action receipt even
    though the anti-replay ledger has correctly marked its ID as consumed.
    """

    def __init__(self, *, mission_issuer: MissionCognitiveReceiptIssuer,
                 action_issuer: ActionCognitiveReceiptIssuer,
                 authority_discovery: AuthorityAwareCapabilityDiscovery) -> None:
        self._mission_issuer = mission_issuer
        self._action_issuer = action_issuer
        self._authority_discovery = authority_discovery

    def verify(self, *, mission: MissionCognitiveReceipt, action: ActionCognitiveReceipt,
               authority: AuthorityReceipt, execution: GovernedSoftwareExecutionResult,
               coi11: ObservationEvidenceStateResult,
               learning: ClosedOperationalLearningResult,
               verification_time: float) -> ReceiptProvenanceResult:
        if not self._mission_issuer.verify(mission):
            raise ReceiptProvenanceError("provenance_invalid_mission_receipt")
        if not self._action_issuer.verify_integrity(action, now=verification_time):
            raise ReceiptProvenanceError("provenance_invalid_action_receipt")
        if not self._authority_discovery.verify_authority_receipt(
            authority, action_receipt=action, now=verification_time
        ):
            raise ReceiptProvenanceError("provenance_invalid_authority_receipt")

        if action.mission_receipt_ref != mission.receipt_id:
            raise ReceiptProvenanceError("provenance_action_mission_lineage_mismatch")
        if action.mission_id != mission.mission_id or authority.mission_id != mission.mission_id:
            raise ReceiptProvenanceError("provenance_mission_context_mismatch")
        if authority.action_receipt_id != action.receipt_id:
            raise ReceiptProvenanceError("provenance_authority_action_lineage_mismatch")
        if authority.action_digest != action.action_digest:
            raise ReceiptProvenanceError("provenance_action_digest_mismatch")
        if authority.capability_id != action.capability_id or authority.ocs_id != action.ocs_id:
            raise ReceiptProvenanceError("provenance_authority_context_mismatch")

        if execution.mission_id != mission.mission_id:
            raise ReceiptProvenanceError("provenance_execution_mission_mismatch")
        if execution.capability_id != action.capability_id or execution.ocs_id != action.ocs_id:
            raise ReceiptProvenanceError("provenance_execution_context_mismatch")

        evidence = coi11.evidence
        state = coi11.state_snapshot
        observation = coi11.observation
        if evidence.mission_id != mission.mission_id or state.mission_id != mission.mission_id:
            raise ReceiptProvenanceError("provenance_evidence_mission_mismatch")
        if evidence.governed_execution_receipt != execution.governed_execution_receipt:
            raise ReceiptProvenanceError("provenance_evidence_execution_lineage_mismatch")
        expected_observation = self._digest({
            "mission_id": observation.mission_id,
            "capability_id": observation.capability_id,
            "ocs_id": observation.ocs_id,
            "governed_execution_receipt": observation.governed_execution_receipt,
            "execution_status": observation.execution_status,
            "observed_effect": dict(observation.observed_effect),
        })
        if evidence.observation_hash != expected_observation:
            raise ReceiptProvenanceError("provenance_observation_hash_invalid")
        expected_evidence = self._digest({
            "observation_hash": expected_observation,
            "adapter_execution_receipt": execution.adapter_execution_receipt.execution_receipt,
            "governed_execution_receipt": execution.governed_execution_receipt,
        })
        if evidence.evidence_receipt != expected_evidence or state.evidence_receipt != expected_evidence:
            raise ReceiptProvenanceError("provenance_evidence_receipt_invalid")
        expected_state = self._digest({
            "mission_id": state.mission_id,
            "previous_state_hash": state.previous_state_hash,
            "evidence_receipt": state.evidence_receipt,
            "state_version": state.state_version,
            "state": dict(state.state),
        })
        if state.state_hash != expected_state:
            raise ReceiptProvenanceError("provenance_state_hash_invalid")

        if learning.feedback.mission_id != mission.mission_id:
            raise ReceiptProvenanceError("provenance_learning_mission_mismatch")
        if learning.feedback.evidence_receipt != evidence.evidence_receipt:
            raise ReceiptProvenanceError("provenance_learning_evidence_mismatch")
        if learning.feedback.state_hash != state.state_hash:
            raise ReceiptProvenanceError("provenance_learning_state_mismatch")
        expected_feedback = self._digest({
            "mission_id": learning.feedback.mission_id,
            "evidence_receipt": learning.feedback.evidence_receipt,
            "state_hash": learning.feedback.state_hash,
            "state_version": learning.feedback.state_version,
            "outcome": learning.feedback.outcome,
            "failed_capability_id": learning.feedback.failed_capability_id,
        })
        if learning.next_plan.feedback_receipt != expected_feedback:
            raise ReceiptProvenanceError("provenance_feedback_receipt_invalid")
        expected_learning = self._digest({
            "previous_plan_receipt": learning.previous_plan.plan_receipt,
            "feedback_receipt": expected_feedback,
            "next_plan_receipt": learning.next_plan.plan_receipt,
            "route_changed": learning.route_changed,
        })
        if learning.learning_receipt != expected_learning:
            raise ReceiptProvenanceError("provenance_learning_receipt_invalid")

        lineage = self._digest({
            "mission_receipt": mission.receipt_id,
            "mission_nonce": mission.nonce,
            "action_receipt": action.receipt_id,
            "action_nonce": action.nonce,
            "authority_receipt": authority.receipt_id,
            "authority_nonce": authority.nonce,
            "governed_execution_receipt": execution.governed_execution_receipt,
            "evidence_receipt": evidence.evidence_receipt,
            "state_hash": state.state_hash,
            "learning_receipt": learning.learning_receipt,
        })
        return ReceiptProvenanceResult(
            mission.mission_id, mission.receipt_id, action.receipt_id, authority.receipt_id,
            execution.governed_execution_receipt, evidence.evidence_receipt, state.state_hash,
            learning.learning_receipt, lineage,
        )

    @staticmethod
    def _digest(payload: object) -> str:
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()
