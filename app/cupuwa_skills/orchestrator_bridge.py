from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_skills.coi_bridge import COISkillExecution, execute_coi_skill
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.registry import SkillRegistry


@dataclass(frozen=True, slots=True)
class OrchestratorReceipt:
    mission_id: str
    operation_id: str
    selected_ocs: str
    composition_receipt: str
    skill_receipt_digest: str
    status: str
    decision_digest: str


@dataclass(frozen=True, slots=True)
class OrchestratorExecution:
    receipt: OrchestratorReceipt
    skill_execution: COISkillExecution


def _decision_digest(payload: dict[str, str]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return sha256(encoded).hexdigest()


def execute_orchestrated_skill(
    registry: SkillRegistry,
    loader: SkillLoader,
    mission: MissionContract,
    *,
    operation_id: str,
    capability: str,
    payload: dict[str, Any],
) -> OrchestratorExecution:
    if not operation_id:
        raise ContractViolation("operation_id_required")
    if capability not in mission.required_capabilities:
        raise ContractViolation("capability_not_bound_to_mission")

    skill_execution = execute_coi_skill(
        registry,
        loader,
        mission,
        capability=capability,
        payload=payload,
    )
    skill_receipt = skill_execution.receipt
    decision_payload = {
        "capability": capability,
        "composition_receipt": skill_execution.composition_receipt,
        "mission_id": mission.mission_id,
        "operation_id": operation_id,
        "selected_ocs": skill_execution.selected_ocs,
        "skill_result_digest": skill_receipt.result_digest,
    }
    receipt = OrchestratorReceipt(
        mission_id=mission.mission_id,
        operation_id=operation_id,
        selected_ocs=skill_execution.selected_ocs,
        composition_receipt=skill_execution.composition_receipt,
        skill_receipt_digest=skill_receipt.result_digest,
        status="SUCCESS",
        decision_digest=_decision_digest(decision_payload),
    )
    return OrchestratorExecution(receipt=receipt, skill_execution=skill_execution)
