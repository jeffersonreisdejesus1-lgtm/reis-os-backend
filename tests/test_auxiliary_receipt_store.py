from pathlib import Path
import sqlite3

import pytest

from app.ocs_instances.receipt import AuxiliaryReceiptState, create_auxiliary_receipt
from app.ocs_instances.receipt_store import (
    AuxiliaryReceiptStore,
    AuxiliaryReceiptStoreError,
)


def receipt() -> object:
    return create_auxiliary_receipt(
        operation_id="operation:1",
        mission_id="mission:1",
        parent_mission_id="mission:parent",
        instance_id=None,
        authority_reference="authority:1",
        executor_id="executor:1",
        capability="bounded-capability",
        payload_fingerprint="payload:1",
        execution_state=AuxiliaryReceiptState.OBSERVED,
        result_reference="result:1",
        evidence_references=(),
        observed_at="2026-09-20T00:00:00Z",
    )


def test_p04_persists_and_reads_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "receipts.sqlite3"
    first = AuxiliaryReceiptStore(path)
    first.begin("operation:1", "payload:1")
    first.complete("operation:1", receipt(), result_reference="result:1")
    restarted = AuxiliaryReceiptStore(path)
    assert restarted.read_operation("operation:1").state == "SUCCEEDED"
    assert restarted.read_receipt("operation:1") == receipt()


def test_replay_returns_existing_record_without_new_execution(tmp_path: Path) -> None:
    store = AuxiliaryReceiptStore(tmp_path / "receipts.sqlite3")
    store.begin("operation:1", "payload:1")
    stored = store.complete("operation:1", receipt(), result_reference="result:1")
    replay = store.begin("operation:1", "payload:1")
    assert replay == stored


def test_conflicting_payload_is_rejected(tmp_path: Path) -> None:
    store = AuxiliaryReceiptStore(tmp_path / "receipts.sqlite3")
    store.begin("operation:1", "payload:1")
    with pytest.raises(AuxiliaryReceiptStoreError, match="payload_conflict"):
        store.begin("operation:1", "payload:2")


def test_corrupt_receipt_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "receipts.sqlite3"
    store = AuxiliaryReceiptStore(path)
    store.begin("operation:1", "payload:1")
    store.complete("operation:1", receipt(), result_reference="result:1")
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE auxiliary_operations SET receipt_json=? WHERE operation_id=?",
            ("{invalid", "operation:1"),
        )
    with pytest.raises(AuxiliaryReceiptStoreError, match="receipt_corrupt"):
        store.read_receipt("operation:1")
