from __future__ import annotations

import sqlite3

import pytest

from app.cupuwa_multi_ocs.contracts import MissionContract
from app.cupuwa_skills.enforcement import enforce_required_skills
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.receipt_store import SkillReceiptStore
from app.cupuwa_skills.registry import SkillDescriptor, SkillRegistry


def mission() -> MissionContract:
    return MissionContract(
        mission_id="mission-1",
        product="CUPUWA",
        increment_id="skills-runtime-binding",
        bound_object="receipt-persistence",
        bound_head="d18f01d47b0ae46d71d459391202b59ab73fda43",
        requested_outcome="persist skill receipt",
        constraints=("no_external_effect",),
        authority_ref="authority:mission-1",
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


def test_enforcement_persists_and_replays_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose_ready(monkeypatch)
    store = SkillReceiptStore(sqlite3.connect(":memory:"))
    calls = 0

    def procedure(payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": payload["value"]}

    loader = SkillLoader({"test-skill": procedure})
    first = enforce_required_skills(
        registry(),
        loader,
        mission(),
        payloads={"run_tests": {"value": True}},
        receipt_store=store,
        operation_id="mission-operation-1",
    )
    second = enforce_required_skills(
        registry(),
        loader,
        mission(),
        payloads={"run_tests": {"value": True}},
        receipt_store=store,
        operation_id="mission-operation-1",
    )
    assert first == second
    assert calls == 1


def test_enforcement_conflicting_replay_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose_ready(monkeypatch)
    store = SkillReceiptStore(sqlite3.connect(":memory:"))
    loader = SkillLoader({"test-skill": lambda payload: {"ok": payload["value"]}})
    enforce_required_skills(
        registry(),
        loader,
        mission(),
        payloads={"run_tests": {"value": True}},
        receipt_store=store,
        operation_id="mission-operation-1",
    )
    try:
        enforce_required_skills(
            registry(),
            loader,
            mission(),
            payloads={"run_tests": {"value": False}},
            receipt_store=store,
            operation_id="mission-operation-1",
        )
    except ValueError as error:
        assert str(error) == "skill_receipt_conflict"
    else:
        raise AssertionError("conflicting replay was not rejected")
