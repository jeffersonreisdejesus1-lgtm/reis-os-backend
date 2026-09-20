"""Atomic canonical-operation coordination for the auxiliary runtime."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


class AuxiliaryConcurrencyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalOperation:
    operation_id: str
    payload_fingerprint: str
    mission_id: str
    authority_reference: str
    capability: str
    state: str
    owner_id: str | None
    receipt_id: str | None
    result_reference: str | None


class AuxiliaryOperationCoordinator:
    """SQLite CAS boundary; it coordinates but never dispatches work."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        with sqlite3.connect(self._path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS auxiliary_canonical_operations (
                    operation_id TEXT PRIMARY KEY,
                    payload_fingerprint TEXT NOT NULL,
                    mission_id TEXT NOT NULL,
                    authority_reference TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    state TEXT NOT NULL,
                    owner_id TEXT,
                    receipt_id TEXT UNIQUE,
                    result_reference TEXT
                )"""
            )

    def claim(
        self,
        *,
        operation_id: str,
        payload_fingerprint: str,
        mission_id: str,
        authority_reference: str,
        capability: str,
        owner_id: str,
    ) -> CanonicalOperation:
        values = (
            operation_id,
            payload_fingerprint,
            mission_id,
            authority_reference,
            capability,
        )
        if not all(values) or not owner_id:
            raise AuxiliaryConcurrencyError("canonical_operation_identity_required")
        with sqlite3.connect(self._path, timeout=10, isolation_level="IMMEDIATE") as db:
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO auxiliary_canonical_operations VALUES "
                    "(?, ?, ?, ?, ?, 'EXECUTING', ?, NULL, NULL)",
                    (*values, owner_id),
                )
                row = db.execute(
                    "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                    (operation_id,),
                ).fetchone()
            else:
                if row[1] != payload_fingerprint:
                    raise AuxiliaryConcurrencyError("canonical_payload_conflict")
                if (
                    row[3] != authority_reference
                    or row[4] != capability
                    or row[2] != mission_id
                ):
                    raise AuxiliaryConcurrencyError("canonical_scope_conflict")
            assert row is not None
            return CanonicalOperation(*row)

    def complete(
        self,
        *,
        operation_id: str,
        owner_id: str,
        receipt_id: str,
        result_reference: str,
    ) -> CanonicalOperation:
        if not all((operation_id, owner_id, receipt_id, result_reference)):
            raise AuxiliaryConcurrencyError("canonical_completion_fields_required")
        with sqlite3.connect(self._path, timeout=10, isolation_level="IMMEDIATE") as db:
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise AuxiliaryConcurrencyError("canonical_operation_absent")
            if row[5] == "SUCCEEDED":
                if row[7] != receipt_id:
                    raise AuxiliaryConcurrencyError("canonical_receipt_conflict")
                return CanonicalOperation(*row)
            if row[5] != "EXECUTING" or row[6] != owner_id:
                raise AuxiliaryConcurrencyError("canonical_stale_owner")
            db.execute(
                "UPDATE auxiliary_canonical_operations SET state='SUCCEEDED', "
                "receipt_id=?, result_reference=? WHERE operation_id=?",
                (receipt_id, result_reference, operation_id),
            )
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            assert row is not None
            return CanonicalOperation(*row)

    def fail(self, *, operation_id: str, owner_id: str) -> CanonicalOperation:
        with sqlite3.connect(self._path, timeout=10, isolation_level="IMMEDIATE") as db:
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None or row[5] != "EXECUTING" or row[6] != owner_id:
                raise AuxiliaryConcurrencyError("canonical_stale_owner")
            db.execute(
                "UPDATE auxiliary_canonical_operations SET state='FAILED' "
                "WHERE operation_id=?",
                (operation_id,),
            )
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            assert row is not None
            return CanonicalOperation(*row)

    def read(self, operation_id: str) -> CanonicalOperation:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT * FROM auxiliary_canonical_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise AuxiliaryConcurrencyError("canonical_operation_absent")
        return CanonicalOperation(*row)
