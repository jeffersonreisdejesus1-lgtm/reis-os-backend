from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_multi_ocs.p0_coi_ingress import discover_and_compose

from .integration import execute_mission_skill
from .loader import SkillLoader
from .registry import SkillRegistry
from .executor import SkillReceipt


@dataclass(frozen=True, slots=True)
class COISkillExecution:
    receipt: SkillReceipt
    composition_receipt: str
    selected_ocs: str


def execute_coi_skill(
    registry: SkillRegistry,
    loader: SkillLoader,
    mission: MissionContract,
    *,
    capability: str,
    payload: dict[str, Any],
) -> COISkillExecution:
    """Execute a registered skill only after COI composition succeeds.

    This boundary resolves and executes a local skill procedure. It does not
    create authority, dispatch an external worker, or claim a material effect.
    """
    if mission.authority_ref is None:
        raise ContractViolation("mission_authority_required")
    if capability not in mission.required_capabilities:
        raise ContractViolation("capability_not_bound_to_mission")

    composition = discover_and_compose()
    if composition.get("status") != "COMPOSED":
        raise ContractViolation("coi_composition_not_ready")

    assignments = composition.get("assignments")
    if not isinstance(assignments, list):
        raise ContractViolation("coi_assignments_invalid")
    assignment = next(
        (
            item
            for item in assignments
            if isinstance(item, dict) and item.get("capability") == capability
        ),
        None,
    )
    if assignment is None:
        raise ContractViolation("coi_capability_not_composed")

    ocs_id = assignment.get("ocs_id")
    composition_receipt = composition.get("composition_receipt")
    if not isinstance(ocs_id, str) or not isinstance(composition_receipt, str):
        raise ContractViolation("coi_composition_receipt_invalid")

    result = execute_mission_skill(
        registry,
        loader,
        capability=capability,
        ocs_id=ocs_id,
        authority_ref=mission.authority_ref,
        payload=payload,
    )
    return COISkillExecution(
        receipt=result.receipt,
        composition_receipt=composition_receipt,
        selected_ocs=ocs_id,
    )
