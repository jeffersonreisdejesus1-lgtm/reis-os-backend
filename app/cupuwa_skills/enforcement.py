from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract

from .coi_bridge import execute_coi_skill
from .executor import SkillReceipt
from .loader import SkillLoader
from .registry import SkillRegistry


@dataclass(frozen=True, slots=True)
class SkillEnforcementReceipt:
    mission_id: str
    status: str
    capability_receipts: tuple[SkillReceipt, ...]
    decision_digest: str


def enforce_required_skills(
    registry: SkillRegistry,
    loader: SkillLoader,
    mission: MissionContract,
    *,
    payloads: dict[str, dict[str, Any]],
) -> SkillEnforcementReceipt:
    """Require every mission capability to cross the COI skill boundary."""
    if not mission.authority_ref:
        raise ContractViolation("mission_authority_required")
    required = tuple(mission.required_capabilities)
    if set(payloads) != set(required):
        raise ContractViolation("required_capabilities_payload_mismatch")

    receipts: list[SkillReceipt] = []
    for capability in required:
        result = execute_coi_skill(
            registry,
            loader,
            mission,
            capability=capability,
            payload=payloads[capability],
        )
        receipts.append(result.receipt)

    decision = {
        "mission_id": mission.mission_id,
        "status": "ENFORCED",
        "skills": [
            {
                "skill_id": receipt.skill_id,
                "skill_version": receipt.skill_version,
                "authority_ref": receipt.authority_ref,
                "status": receipt.status,
                "result_digest": receipt.result_digest,
            }
            for receipt in receipts
        ],
    }
    digest = sha256(
        json.dumps(decision, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SkillEnforcementReceipt(
        mission_id=mission.mission_id,
        status="ENFORCED",
        capability_receipts=tuple(receipts),
        decision_digest=digest,
    )
