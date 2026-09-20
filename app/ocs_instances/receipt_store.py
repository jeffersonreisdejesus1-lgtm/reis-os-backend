"""Durable, fail-closed operation and auxiliary receipt readback."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.ocs_instances.receipt import (
    AuxiliaryEvidenceReference,
    AuxiliaryReceipt,
    AuxiliaryReceiptState,
)


class AuxiliaryReceiptStoreError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OperationRecord:
    operation_id: str
    payload_fingerprint: str
    state: str
    result_reference: str | None
    receipt_id: str | None


class AuxiliaryReceiptStore:
    """SQLite persistence boundary; it never dispatches an operation."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        with sqlite3.connect(self._path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS auxiliary_operations (
                    operation_id TEXT PRIMARY KEY,
                    payload_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_reference TEXT,
                    receipt_json TEXT,
                    receipt_id TEXT
                )"""
            )

    def begin(self, operation_id: str, payload_fingerprint: str) -> OperationRecord:
        if not operation_id or not payload_fingerprint:
            raise AuxiliaryReceiptStoreError("operation_identity_required")
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT * FROM auxiliary_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row:
                if row[1] != payload_fingerprint:
                    raise AuxiliaryReceiptStoreError("payload_conflict")
                return OperationRecord(row[0], row[1], row[2], row[3], row[5])
            db.execute(
                "INSERT INTO auxiliary_operations VALUES "
                "(?, ?, 'PENDING', NULL, NULL, NULL)",
                (operation_id, payload_fingerprint),
            )
            db.commit()
        return OperationRecord(operation_id, payload_fingerprint, "PENDING", None, None)

    def complete(
        self,
        operation_id: str,
        receipt: AuxiliaryReceipt,
        *,
        result_reference: str | None,
    ) -> OperationRecord:
        if receipt.operation_id != operation_id:
            raise AuxiliaryReceiptStoreError("receipt_operation_mismatch")
        if receipt.receipt_id != receipt.canonical_identity():
            raise AuxiliaryReceiptStoreError("receipt_integrity_failure")
        payload = json.dumps(receipt.to_dict(), sort_keys=True)
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT payload_fingerprint, state, receipt_id "
                "FROM auxiliary_operations "
                "WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise AuxiliaryReceiptStoreError("operation_not_found")
            if row[1] == "SUCCEEDED":
                if row[2] != receipt.receipt_id:
                    raise AuxiliaryReceiptStoreError("receipt_replay_conflict")
                return self.read_operation(operation_id)
            db.execute(
                "UPDATE auxiliary_operations SET state='SUCCEEDED', "
                "result_reference=?, "
                "receipt_json=?, receipt_id=? WHERE operation_id=?",
                (result_reference, payload, receipt.receipt_id, operation_id),
            )
            db.commit()
        return self.read_operation(operation_id)

    def read_operation(self, operation_id: str) -> OperationRecord:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT operation_id, payload_fingerprint, state, result_reference, "
                "receipt_id FROM auxiliary_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise AuxiliaryReceiptStoreError("operation_absent")
        return OperationRecord(*row)

    def read_receipt(self, operation_id: str) -> AuxiliaryReceipt:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT receipt_json FROM auxiliary_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if row is None or row[0] is None:
            raise AuxiliaryReceiptStoreError("receipt_absent")
        try:
            value = json.loads(row[0])
            evidence = tuple(
                AuxiliaryEvidenceReference(**item)
                for item in value["evidence_references"]
            )
            value["evidence_references"] = evidence
            value["execution_state"] = AuxiliaryReceiptState(value["execution_state"])
            receipt = AuxiliaryReceipt(**value)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise AuxiliaryReceiptStoreError("receipt_corrupt") from error
        if receipt.operation_id != operation_id:
            raise AuxiliaryReceiptStoreError("receipt_operation_mismatch")
        if receipt.receipt_id != receipt.canonical_identity():
            raise AuxiliaryReceiptStoreError("receipt_integrity_failure")
        return receipt
