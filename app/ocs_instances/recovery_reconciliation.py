"""Fail-closed recovery for interrupted auxiliary operations."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class RecoveryReconciliationError(RuntimeError):
    pass


class RecoveryState:
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class RecoveryRecord:
    operation_id: str
    payload_fingerprint: str
    state: str
    result_reference: str | None
    recovery_receipt_id: str | None


@dataclass(frozen=True, slots=True)
class RecoveryReceipt:
    receipt_id: str
    operation_id: str
    prior_state: str
    resulting_state: str
    disposition: str
    result_reference: str | None


class AuxiliaryRecoveryStore:
    """Durable recovery ledger; it never dispatches or retries work."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        with sqlite3.connect(self._path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS auxiliary_recovery (
                    operation_id TEXT PRIMARY KEY,
                    payload_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_reference TEXT,
                    recovery_receipt_json TEXT,
                    recovery_receipt_id TEXT
                )"""
            )

    def register(self, operation_id: str, payload_fingerprint: str) -> RecoveryRecord:
        if not operation_id or not payload_fingerprint:
            raise RecoveryReconciliationError("recovery_identity_required")
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT operation_id, payload_fingerprint, state, result_reference, "
                "recovery_receipt_id FROM auxiliary_recovery WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is not None:
                if row[1] != payload_fingerprint:
                    raise RecoveryReconciliationError("recovery_payload_conflict")
                return RecoveryRecord(*row)
            db.execute(
                "INSERT INTO auxiliary_recovery VALUES (?, ?, ?, NULL, NULL, NULL)",
                (operation_id, payload_fingerprint, RecoveryState.PENDING),
            )
        return RecoveryRecord(
            operation_id, payload_fingerprint, RecoveryState.PENDING, None, None
        )

    def mark_executing(self, operation_id: str) -> RecoveryRecord:
        return self._transition(operation_id, RecoveryState.EXECUTING)

    def mark_unknown(self, operation_id: str) -> RecoveryRecord:
        return self._transition(operation_id, RecoveryState.UNKNOWN)

    def mark_failed(self, operation_id: str) -> RecoveryRecord:
        return self._transition(operation_id, RecoveryState.FAILED)

    def recover_after_restart(self, operation_id: str) -> RecoveryRecord:
        record = self.read(operation_id)
        if record.state in {RecoveryState.PENDING, RecoveryState.EXECUTING}:
            return self._transition(operation_id, RecoveryState.UNKNOWN)
        return record

    def reconcile(
        self,
        operation_id: str,
        *,
        effect_proven: bool,
        result_reference: str | None = None,
    ) -> RecoveryRecord:
        record = self.read(operation_id)
        if record.state not in {
            RecoveryState.UNKNOWN,
            RecoveryState.RECONCILING,
            RecoveryState.HOLD,
        }:
            raise RecoveryReconciliationError("recovery_reconciliation_not_required")
        if not effect_proven:
            return self._commit_recovery(
                record, RecoveryState.HOLD, "EFFECT_UNDETERMINED", None
            )
        if not result_reference:
            raise RecoveryReconciliationError("recovery_result_reference_required")
        return self._commit_recovery(
            record, RecoveryState.RECONCILED, "EFFECT_RECONCILED", result_reference
        )

    def retry_eligibility(
        self,
        operation_id: str,
        *,
        no_effect_proven: bool,
        idempotency_verified: bool,
    ) -> bool:
        record = self.read(operation_id)
        if record.state in {RecoveryState.UNKNOWN, RecoveryState.HOLD} and (
            no_effect_proven or idempotency_verified
        ):
            return True
        return False

    def read(self, operation_id: str) -> RecoveryRecord:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT operation_id, payload_fingerprint, state, result_reference, "
                "recovery_receipt_id FROM auxiliary_recovery WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise RecoveryReconciliationError("recovery_operation_absent")
        return RecoveryRecord(*row)

    def read_receipt(self, operation_id: str) -> RecoveryReceipt:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT recovery_receipt_json FROM auxiliary_recovery "
                "WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if row is None or row[0] is None:
            raise RecoveryReconciliationError("recovery_receipt_absent")
        try:
            value = json.loads(row[0])
            receipt = RecoveryReceipt(**value)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise RecoveryReconciliationError("recovery_receipt_corrupt") from error
        if receipt.receipt_id != self._receipt_id(receipt):
            raise RecoveryReconciliationError("recovery_receipt_integrity_failure")
        return receipt

    def _transition(self, operation_id: str, state: str) -> RecoveryRecord:
        record = self.read(operation_id)
        if record.state in {
            RecoveryState.SUCCEEDED,
            RecoveryState.FAILED,
            RecoveryState.RECONCILED,
        }:
            return record
        with sqlite3.connect(self._path) as db:
            db.execute(
                "UPDATE auxiliary_recovery SET state=? WHERE operation_id=?",
                (state, operation_id),
            )
        return self.read(operation_id)

    def _commit_recovery(
        self,
        record: RecoveryRecord,
        state: str,
        disposition: str,
        result: str | None,
    ) -> RecoveryRecord:
        receipt_data = {
            "operation_id": record.operation_id,
            "prior_state": record.state,
            "resulting_state": state,
            "disposition": disposition,
            "result_reference": result,
        }
        receipt = RecoveryReceipt(
            receipt_id=self._receipt_id_from_payload(receipt_data),
            operation_id=record.operation_id,
            prior_state=record.state,
            resulting_state=state,
            disposition=disposition,
            result_reference=result,
        )
        payload = json.dumps({
            "receipt_id": receipt.receipt_id,
            "operation_id": receipt.operation_id,
            "prior_state": receipt.prior_state,
            "resulting_state": receipt.resulting_state,
            "disposition": receipt.disposition,
            "result_reference": receipt.result_reference,
        }, sort_keys=True, separators=(",", ":"))
        with sqlite3.connect(self._path) as db:
            db.execute(
                "UPDATE auxiliary_recovery SET state=?, result_reference=?, "
                "recovery_receipt_json=?, recovery_receipt_id=? "
                "WHERE operation_id=?",
                (state, result, payload, receipt.receipt_id, record.operation_id),
            )
        return self.read(record.operation_id)

    @staticmethod
    def _receipt_id(receipt: RecoveryReceipt) -> str:
        payload = {
            "operation_id": receipt.operation_id,
            "prior_state": receipt.prior_state,
            "resulting_state": receipt.resulting_state,
            "disposition": receipt.disposition,
            "result_reference": receipt.result_reference,
        }
        return AuxiliaryRecoveryStore._receipt_id_from_payload(payload)

    @staticmethod
    def _receipt_id_from_payload(payload: Mapping[str, object]) -> str:
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
