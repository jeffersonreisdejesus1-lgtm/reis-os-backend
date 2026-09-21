from __future__ import annotations

import pytest

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_skills.enforcement import enforce_required_skills
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.registry import SkillDescriptor, SkillRegistry


def mission(authority_ref: str | None = "authority:mission-1") -> MissionContract:
    return MissionContract(
        mission_id="mission-1",
        product="CUPUWA",
        increment_id="skills-enforcement",
        bound_object="required-skills",
        bound_head="581b159e5099d80b5f3519faa7dca40bb6ce3ab9",
        requested_outcome="enforce skills",
        constraints=("no_external_effect",),
        authority_ref=authority_ref,
        required_capabilities=("run_tests",),
        evidence_policy="receipt_required",
        completion_policy="qualified_only",
    )


def registry() -> SkillRegistry:
    return SkillRegistry(
        [
            SkillDescriptor(
                skill_id="test-skill",
                version="1.0.0",
                capabilities=frozenset({"run_tests"}),
                compatible_ocs=frozenset({"SOFIA"}),
            )
        ]
    )


def compose_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.cupuwa_skills.coi_bridge.discover_and_compose",
        lambda: {
            "status": "COMPOSED",
            "assignments": [{"capability": "run_tests", "ocs_id": "SOFIA"}],
            "composition_receipt": "composition-1",
        },
    )


def test_all_required_capabilities_are_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose_ready(monkeypatch)
    result = enforce_required_skills(
        registry(),
        SkillLoader({"test-skill": lambda payload: {"ok": payload["value"]}}),
        mission(),
        payloads={"run_tests": {"value": True}},
    )
    assert result.status == "ENFORCED"
    assert len(result.capability_receipts) == 1
    assert result.decision_digest


def test_missing_skill_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    compose_ready(monkeypatch)
    with pytest.raises(LookupError, match="not_unique"):
        enforce_required_skills(
            SkillRegistry(),
            SkillLoader({}),
            mission(),
            payloads={"run_tests": {}},
        )


def test_authority_is_required_before_enforcement() -> None:
    with pytest.raises(ContractViolation, match="authority"):
        enforce_required_skills(
            registry(),
            SkillLoader({"test-skill": lambda payload: payload}),
            mission(None),
            payloads={"run_tests": {}},
        )


def test_payloads_must_cover_exact_required_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose_ready(monkeypatch)
    with pytest.raises(
        ContractViolation, match="required_capabilities_payload_mismatch"
    ):
        enforce_required_skills(
            registry(),
            SkillLoader({"test-skill": lambda payload: payload}),
            mission(),
            payloads={},
        )
