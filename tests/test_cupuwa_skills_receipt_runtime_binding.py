from __future__ import annotations

import sqlite3

from app.cupuwa_skills.enforcement import enforce_required_skills
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.receipt_store import SkillReceiptStore
from tests.test_cupuwa_skills_enforcement import mission, registry, compose_ready


def test_enforcement_persists_and_replays_without_execution(monkeypatch) -> None:
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


def test_enforcement_conflicting_replay_fails_closed(monkeypatch) -> None:
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
