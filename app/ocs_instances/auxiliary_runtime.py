"""Governed, durable adapter for auxiliary instance requests.

This module binds an already-authorized host executor to the existing instance
store.  It does not mint authority and deliberately refuses to simulate a
worker when no executor is supplied.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from app.ocs_instances.contracts import InstanceBindingError


@dataclass(frozen=True, slots=True)
class AuxiliaryAuthority:
    authority_ref: str
    allowed_scope: tuple[str, ...]
    requesting_ocs: str


@dataclass(frozen=True, slots=True)
class SpawnResult:
    operation_id: str
    instance_id: str
    parent_mission_id: str
    execution_state: str
    result_reference: str | None
    receipt_reference: str


class AuxiliaryInstanceRuntime:
    """Durable idempotency/reconciliation boundary for host instance creation."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = str(database_path)
        with sqlite3.connect(self._path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS auxiliary_operations (
                    operation_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_json TEXT,
                    receipt_reference TEXT NOT NULL
                )"""
            )

    @staticmethod
    def _payload_hash(
        parent_mission_id: str,
        requesting_ocs: str,
        target_capability: str,
        bounded_task: str,
        authority: AuxiliaryAuthority,
    ) -> str:
        payload = {
            "parent_mission_id": parent_mission_id,
            "requesting_ocs": requesting_ocs,
            "target_capability": target_capability,
            "bounded_task": bounded_task,
            "authority_ref": authority.authority_ref,
            "allowed_scope": authority.allowed_scope,
        }
        return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def spawn_instance(
        self,
        *,
        parent_mission_id: str,
        requesting_ocs: str,
        target_capability: str,
        bounded_task: str,
        authority: AuxiliaryAuthority | None,
        operation_id: str,
        executor: Callable[[str, str, str], tuple[str, str, str]] | None,
    ) -> SpawnResult:
        if not authority or not authority.authority_ref:
            raise PermissionError("auxiliary_authority_required")
        if authority.requesting_ocs != requesting_ocs:
            raise PermissionError("auxiliary_authority_scope_mismatch")
        if target_capability not in authority.allowed_scope:
            raise PermissionError("auxiliary_capability_outside_scope")
        if not all((parent_mission_id, requesting_ocs, bounded_task, operation_id)):
            raise ValueError("auxiliary_request_fields_required")
        if executor is None:
            raise InstanceBindingError("material_instance_executor_required")

        fingerprint = self._payload_hash(
            parent_mission_id,
            requesting_ocs,
            target_capability,
            bounded_task,
            authority,
        )
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT payload_hash, state, result_json, receipt_reference "
                "FROM auxiliary_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise InstanceBindingError("IDEMPOTENCY_CONFLICT")
                if row[1] == "SUCCEEDED" and row[2]:
                    return SpawnResult(**json.loads(row[2]))
                raise InstanceBindingError(
                    "auxiliary_operation_requires_reconciliation"
                )
            receipt = (
                "spawn:"
                f"{sha256((operation_id + fingerprint).encode()).hexdigest()}"
            )
            try:
                db.execute(
                    "INSERT INTO auxiliary_operations VALUES "
                    "(?, ?, 'PENDING', NULL, ?)",
                    (operation_id, fingerprint, receipt),
                )
            except sqlite3.IntegrityError as error:
                raise InstanceBindingError(
                    "auxiliary_operation_concurrent_reconciliation_required"
                ) from error
            db.commit()

        try:
            instance_id, state, result_reference = executor(
                parent_mission_id, target_capability, bounded_task
            )
        except Exception:
            with sqlite3.connect(self._path) as db:
                db.execute(
                    "UPDATE auxiliary_operations SET state='FAILED' "
                    "WHERE operation_id=?",
                    (operation_id,),
                )
            raise

        result = SpawnResult(
            operation_id=operation_id,
            instance_id=instance_id,
            parent_mission_id=parent_mission_id,
            execution_state=state,
            result_reference=result_reference,
            receipt_reference=receipt,
        )
        with sqlite3.connect(self._path) as db:
            db.execute(
                "UPDATE auxiliary_operations SET state='SUCCEEDED', result_json=? "
                "WHERE operation_id=? AND state='PENDING'",
                (json.dumps(asdict(result), sort_keys=True), operation_id),
            )
            db.commit()
        return result

    def reconcile(self, operation_id: str) -> SpawnResult | None:
        with sqlite3.connect(self._path) as db:
            row = db.execute(
                "SELECT state, result_json FROM auxiliary_operations "
                "WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        if not row or row[0] != "SUCCEEDED" or not row[1]:
            return None
        return SpawnResult(**json.loads(row[1]))
