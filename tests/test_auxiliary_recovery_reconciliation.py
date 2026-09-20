from pathlib import Path

import pytest

from app.ocs_instances.recovery_reconciliation import (
    AuxiliaryRecoveryStore,
    RecoveryReconciliationError,
    RecoveryState,
)


def test_pending_restart_becomes_unknown_without_dispatch(tmp_path: Path) -> None:
    path = tmp_path / "recovery.sqlite3"
    first = AuxiliaryRecoveryStore(path)
    first.register("operation:1", "payload:1")
    restarted = AuxiliaryRecoveryStore(path)
    record = restarted.recover_after_restart("operation:1")
    assert record.state == RecoveryState.UNKNOWN


def test_executing_restart_becomes_unknown_without_dispatch(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    store.mark_executing("operation:1")
    assert store.recover_after_restart("operation:1").state == RecoveryState.UNKNOWN


def test_unknown_with_undetermined_effect_stays_hold(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    store.mark_unknown("operation:1")
    record = store.reconcile("operation:1", effect_proven=False)
    assert record.state == RecoveryState.HOLD
    assert store.read_receipt("operation:1").disposition == "EFFECT_UNDETERMINED"


def test_proven_external_effect_is_reconciled(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    store.mark_unknown("operation:1")
    record = store.reconcile(
        "operation:1", effect_proven=True, result_reference="result:1"
    )
    assert record.state == RecoveryState.RECONCILED
    assert store.read_receipt("operation:1").result_reference == "result:1"


def test_failed_executor_is_terminal_failed(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    assert store.mark_failed("operation:1").state == RecoveryState.FAILED


def test_retry_requires_proof_or_verified_idempotency(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    store.mark_unknown("operation:1")
    assert not store.retry_eligibility(
        "operation:1", no_effect_proven=False, idempotency_verified=False
    )
    assert store.retry_eligibility(
        "operation:1", no_effect_proven=True, idempotency_verified=False
    )


def test_payload_conflict_and_missing_operation_fail_closed(tmp_path: Path) -> None:
    store = AuxiliaryRecoveryStore(tmp_path / "recovery.sqlite3")
    store.register("operation:1", "payload:1")
    with pytest.raises(RecoveryReconciliationError, match="payload_conflict"):
        store.register("operation:1", "payload:2")
    with pytest.raises(RecoveryReconciliationError, match="operation_absent"):
        store.read("operation:missing")

