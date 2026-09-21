from __future__ import annotations

import pytest

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_skills.executor import SkillReceipt
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.orchestrator_bridge import (
    OrchestratorExecution,
    execute_orchestrated_skill,
)
from app.cupuwa_skills.registry import SkillRegistry
from app.cupuwa_skills.coi_bridge import COISkillExecution


def mission() -> MissionContract:
    return MissionContract(
        mission_id="mission-1",
        product="CUPUWA",
        increment_id="W03",
        bound_object="orchestrator",
        bound_head="head-1",
        requested_outcome="local skill result",
        constraints=("no_external_effect",),
        authority_ref="authority-1",
        required_capabilities=("product",),
        evidence_policy="receipt",
        completion_policy="qualified",
    )


def test_missing_operation_id_fails_closed() -> None:
    with pytest.raises(ContractViolation, match="operation_id_required"):
        execute_orchestrated_skill(
            SkillRegistry(),
            SkillLoader({}),
            mission(),
            operation_id="",
            capability="product",
            payload={},
        )


def test_unbound_capability_fails_closed() -> None:
    with pytest.raises(
        ContractViolation,
        match="capability_not_bound_to_mission",
    ):
        execute_orchestrated_skill(
            SkillRegistry(),
            SkillLoader({}),
            mission(),
            operation_id="operation-1",
            capability="security",
            payload={},
        )


def test_orchestrator_receipt_preserves_causal_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.cupuwa_skills.orchestrator_bridge.execute_coi_skill",
        lambda *args, **kwargs: COISkillExecution(
            receipt=SkillReceipt(
                skill_id="skill-1",
                skill_version="1.0",
                authority_ref="authority-1",
                status="SUCCESS",
                result_digest="result-1",
            ),
            composition_receipt="composition-1",
            selected_ocs="OCS-1",
        ),
    )
    result = execute_orchestrated_skill(
        SkillRegistry(),
        SkillLoader({}),
        mission(),
        operation_id="operation-1",
        capability="product",
        payload={"value": 1},
    )
    assert isinstance(result, OrchestratorExecution)
    assert result.receipt.mission_id == "mission-1"
    assert result.receipt.operation_id == "operation-1"
    assert result.receipt.selected_ocs == "OCS-1"
    assert result.receipt.skill_receipt_digest == "result-1"
    assert result.receipt.status == "SUCCESS"
