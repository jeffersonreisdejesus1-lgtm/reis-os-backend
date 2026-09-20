from __future__ import annotations

import pytest

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_skills.coi_bridge import execute_coi_skill
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.registry import SkillDescriptor, SkillRegistry


def mission() -> MissionContract:
    return MissionContract(
        mission_id="mission-1",
        product="CUPUWA",
        increment_id="skills-foundation",
        bound_object="skill-execution",
        bound_head="dbf996f133a90815d41fe08f6ff5746f27b24c33",
        requested_outcome="run a bounded skill",
        constraints=("no_external_effect",),
        authority_ref="authority:mission-1",
        required_capabilities=("run_tests",),
        evidence_policy="receipt_required",
        completion_policy="qualified_only",
    )


def test_coi_composition_routes_to_skill_and_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.cupuwa_skills.coi_bridge.discover_and_compose",
        lambda: {
            "status": "COMPOSED",
            "assignments": [{"capability": "run_tests", "ocs_id": "SOFIA"}],
            "composition_receipt": "composition-1",
        },
    )
    registry = SkillRegistry(
        [
            SkillDescriptor(
                skill_id="test-skill",
                version="1.0.0",
                capabilities=frozenset({"run_tests"}),
                compatible_ocs=frozenset({"SOFIA"}),
            )
        ]
    )
    loader = SkillLoader({"test-skill": lambda payload: {"ok": payload["value"]}})
    result = execute_coi_skill(
        registry,
        loader,
        mission(),
        capability="run_tests",
        payload={"value": True},
    )
    assert result.selected_ocs == "SOFIA"
    assert result.composition_receipt == "composition-1"
    assert result.receipt.status == "SUCCESS"


def test_coi_rejects_capability_outside_mission() -> None:
    with pytest.raises(ContractViolation, match="capability_not_bound_to_mission"):
        execute_coi_skill(
            SkillRegistry(),
            SkillLoader({}),
            mission(),
            capability="write_code",
            payload={},
        )


def test_coi_rejects_non_composed_ingress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.cupuwa_skills.coi_bridge.discover_and_compose",
        lambda: {"status": "HOLD"},
    )
    with pytest.raises(ContractViolation, match="coi_composition_not_ready"):
        execute_coi_skill(
            SkillRegistry(),
            SkillLoader({}),
            mission(),
            capability="run_tests",
            payload={},
        )
