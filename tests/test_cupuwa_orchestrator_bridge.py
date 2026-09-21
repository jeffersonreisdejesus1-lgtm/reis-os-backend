from __future__ import annotations

from typing import Any

import pytest

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_multi_ocs.p0_coi_ingress import discover_and_compose
from app.cupuwa_skills.coi_bridge import COISkillExecution
from app.cupuwa_skills.executor import SkillReceipt
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.orchestrator_bridge import (
    OrchestratorExecution,
    execute_orchestrated_skill,
)
from app.cupuwa_skills.registry import SkillDescriptor, SkillRegistry


def mission(
    *,
    authority_ref: str = "authority-1",
    required_capabilities: tuple[str, ...] = ("product",),
) -> MissionContract:
    return MissionContract(
        mission_id="mission-1",
        product="CUPUWA",
        increment_id="W03",
        bound_object="orchestrator",
        bound_head="head-1",
        requested_outcome="local skill result",
        constraints=("no_external_effect",),
        authority_ref=authority_ref,
        required_capabilities=required_capabilities,
        evidence_policy="receipt",
        completion_policy="qualified",
    )


def _product_ocs() -> str:
    composition = discover_and_compose()
    assert composition.get("status") == "COMPOSED"
    assignments = composition.get("assignments")
    assert isinstance(assignments, list)
    match = next(
        item
        for item in assignments
        if isinstance(item, dict) and item.get("capability") == "product"
    )
    ocs_id = match["ocs_id"]
    assert isinstance(ocs_id, str)
    return ocs_id


def _bound_stack(
    *,
    capability: str = "product",
    ocs_id: str | None = None,
    procedure: Any | None = None,
) -> tuple[SkillRegistry, SkillLoader]:
    selected = ocs_id or _product_ocs()
    registry = SkillRegistry(
        [
            SkillDescriptor(
                skill_id="product-skill",
                version="1.0.0",
                capabilities=frozenset({capability}),
                compatible_ocs=frozenset({selected}),
            )
        ]
    )
    loader = SkillLoader(
        {
            "product-skill": procedure
            or (lambda payload: {"ok": True, "n": payload.get("n", 0)})
        }
    )
    return registry, loader


def test_o01_valid_mission_reaches_real_coi() -> None:
    composition = discover_and_compose()
    registry, loader = _bound_stack()
    result = execute_orchestrated_skill(
        registry,
        loader,
        mission(),
        operation_id="operation-o01",
        capability="product",
        payload={"n": 1},
    )
    assert isinstance(result, OrchestratorExecution)
    assert result.receipt.status == "SUCCESS"
    assert result.receipt.mission_id == "mission-1"
    assert result.receipt.operation_id == "operation-o01"
    assert result.receipt.selected_ocs == _product_ocs()
    assert result.receipt.composition_receipt == composition["composition_receipt"]
    assert result.skill_execution.composition_receipt == (
        composition["composition_receipt"]
    )
    assert result.skill_execution.receipt.status == "SUCCESS"


def test_o02_mission_without_authority_fails_closed() -> None:
    registry, loader = _bound_stack()
    unauthorized = mission()
    object.__setattr__(unauthorized, "authority_ref", None)
    with pytest.raises(ContractViolation, match="mission_authority_required"):
        execute_orchestrated_skill(
            registry,
            loader,
            unauthorized,
            operation_id="operation-o02",
            capability="product",
            payload={"n": 1},
        )


def test_o03_unbound_capability_fails_closed() -> None:
    registry, loader = _bound_stack()
    with pytest.raises(
        ContractViolation,
        match="capability_not_bound_to_mission",
    ):
        execute_orchestrated_skill(
            registry,
            loader,
            mission(),
            operation_id="operation-o03",
            capability="security",
            payload={},
        )


def test_o04_invalid_composition_fails_closed() -> None:
    registry, loader = _bound_stack()
    with pytest.raises(ContractViolation, match="coi_capability_not_composed"):
        execute_orchestrated_skill(
            registry,
            loader,
            mission(required_capabilities=("not_composed_capability",)),
            operation_id="operation-o04",
            capability="not_composed_capability",
            payload={},
        )


def test_o05_missing_executor_fails_closed() -> None:
    selected = _product_ocs()
    registry = SkillRegistry(
        [
            SkillDescriptor(
                skill_id="product-skill",
                version="1.0.0",
                capabilities=frozenset({"product"}),
                compatible_ocs=frozenset({selected}),
            )
        ]
    )
    loader = SkillLoader({})
    with pytest.raises(LookupError, match="skill_procedure_not_available"):
        execute_orchestrated_skill(
            registry,
            loader,
            mission(),
            operation_id="operation-o05",
            capability="product",
            payload={"n": 1},
        )


def test_o06_replay_preserves_canonical_operation() -> None:
    registry, loader = _bound_stack()
    first = execute_orchestrated_skill(
        registry,
        loader,
        mission(),
        operation_id="operation-o06",
        capability="product",
        payload={"n": 6},
    )
    second = execute_orchestrated_skill(
        registry,
        loader,
        mission(),
        operation_id="operation-o06",
        capability="product",
        payload={"n": 6},
    )
    assert first.receipt.operation_id == second.receipt.operation_id
    assert first.receipt.decision_digest == second.receipt.decision_digest
    assert first.receipt.skill_receipt_digest == second.receipt.skill_receipt_digest
    assert first.receipt.composition_receipt == second.receipt.composition_receipt


def test_o07_receipt_keeps_causal_binding() -> None:
    registry, loader = _bound_stack()
    result = execute_orchestrated_skill(
        registry,
        loader,
        mission(),
        operation_id="operation-o07",
        capability="product",
        payload={"n": 7},
    )
    assert result.receipt.mission_id == "mission-1"
    assert result.receipt.operation_id == "operation-o07"
    assert result.receipt.selected_ocs == result.skill_execution.selected_ocs
    assert (
        result.receipt.composition_receipt
        == result.skill_execution.composition_receipt
    )
    assert (
        result.receipt.skill_receipt_digest
        == result.skill_execution.receipt.result_digest
    )


def test_o08_restart_readback_preserves_identity() -> None:
    payload = {"n": 8}
    first_registry, first_loader = _bound_stack()
    first = execute_orchestrated_skill(
        first_registry,
        first_loader,
        mission(),
        operation_id="operation-o08",
        capability="product",
        payload=payload,
    )
    restarted_registry, restarted_loader = _bound_stack()
    second = execute_orchestrated_skill(
        restarted_registry,
        restarted_loader,
        mission(),
        operation_id="operation-o08",
        capability="product",
        payload=payload,
    )
    assert first.receipt.operation_id == second.receipt.operation_id
    assert first.receipt.mission_id == second.receipt.mission_id
    assert first.receipt.decision_digest == second.receipt.decision_digest
    assert first.receipt.selected_ocs == second.receipt.selected_ocs
    assert first.receipt.composition_receipt == second.receipt.composition_receipt


def test_missing_operation_id_fails_closed() -> None:
    registry, loader = _bound_stack()
    with pytest.raises(ContractViolation, match="operation_id_required"):
        execute_orchestrated_skill(
            registry,
            loader,
            mission(),
            operation_id="",
            capability="product",
            payload={},
        )


def test_isolated_mock_does_not_replace_real_coi(
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
        operation_id="operation-isolated",
        capability="product",
        payload={"value": 1},
    )
    assert result.receipt.skill_receipt_digest == "result-1"
