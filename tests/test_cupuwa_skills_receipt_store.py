from __future__ import annotations

import sqlite3

import pytest

from app.cupuwa_skills.executor import SkillReceipt
from app.cupuwa_skills.receipt_store import SkillReceiptStore


def receipt() -> SkillReceipt:
    return SkillReceipt(
        skill_id="test-skill",
        skill_version="1.0.0",
        authority_ref="authority:mission-1",
        status="SUCCESS",
        result_digest="result-1",
    )


def test_persists_and_recovers_after_reopen(tmp_path) -> None:
    path = tmp_path / "receipts.sqlite"
    first = SkillReceiptStore(sqlite3.connect(path))
    persisted = first.persist(
        operation_id="op-1",
        mission_id="mission-1",
        receipt=receipt(),
        payload={"value": True},
    )
    second = SkillReceiptStore(sqlite3.connect(path))
    assert second.recover("op-1") == persisted


def test_identical_replay_returns_canonical_receipt() -> None:
    store = SkillReceiptStore(sqlite3.connect(":memory:"))
    first = store.persist(
        operation_id="op-1",
        mission_id="mission-1",
        receipt=receipt(),
        payload={"value": True},
    )
    assert store.persist(
        operation_id="op-1",
        mission_id="mission-1",
        receipt=receipt(),
        payload={"value": True},
    ) == first


def test_conflicting_replay_fails_closed() -> None:
    store = SkillReceiptStore(sqlite3.connect(":memory:"))
    store.persist(
        operation_id="op-1",
        mission_id="mission-1",
        receipt=receipt(),
        payload={"value": True},
    )
    with pytest.raises(ValueError, match="skill_receipt_conflict"):
        store.persist(
            operation_id="op-1",
            mission_id="mission-1",
            receipt=receipt(),
            payload={"value": False},
        )


def test_missing_receipt_is_not_success() -> None:
    store = SkillReceiptStore(sqlite3.connect(":memory:"))
    with pytest.raises(LookupError, match="not_found"):
        store.recover("unknown")


def test_corrupted_receipt_is_rejected() -> None:
    connection = sqlite3.connect(":memory:")
    store = SkillReceiptStore(connection)
    store.persist(
        operation_id="op-1",
        mission_id="mission-1",
        receipt=receipt(),
        payload={"value": True},
    )
    connection.execute(
        "UPDATE skill_receipts SET result_digest = 'corrupt' "
        "WHERE operation_id = 'op-1'"
    )
    connection.commit()
    with pytest.raises(ValueError, match="corrupt"):
        store.recover("op-1")
