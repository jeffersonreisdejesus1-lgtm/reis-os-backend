from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from .distributed_ownership import Lease, LeaseConflict, StaleOwner, validate_replay
from .distributed_recovery import RecoveryDecision, RecoveryObservation, decide_recovery
from .distributed_recovery_receipt import RecoveryReceipt, reconcile_receipt
from .distributed_storage import (
    DistributedOperationKey,
    DistributedOperationRecord,
    DistributedOperationState,
)

SCHEMA_VERSION = "1.0"
LEASE_SECONDS = 30


def payload_fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


class PosixFileDistributedStorage:
    """Shared-directory backend usable by independent OS processes.

    Persistence is JSON + exclusive lock files on a shared filesystem.
    This is not SQLite and not an in-memory object.
    """

    backend_name = "posix-file-store"
    backend_version = "1.0"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        (self.root / "ops").mkdir(parents=True, exist_ok=True)
        (self.root / "leases").mkdir(parents=True, exist_ok=True)
        (self.root / "receipts").mkdir(parents=True, exist_ok=True)

    def _op_path(self, operation_id: str) -> Path:
        return self.root / "ops" / f"{operation_id}.json"

    def _lease_path(self, operation_id: str) -> Path:
        return self.root / "leases" / f"{operation_id}.json"

    def _lock_fd(self, operation_id: str):
        lock_path = self.root / "ops" / f"{operation_id}.lock"
        handle = open(lock_path, "a+", encoding="utf-8")
        if os.name == "posix":
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def _load_raw(self, operation_id: str) -> dict | None:
        path = self._op_path(operation_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LeaseConflict("corrupt_operation_record") from exc

    def _dump(self, record: DistributedOperationRecord, extra: dict | None = None) -> None:
        payload = {
            "key": asdict(record.key),
            "state": record.state.value,
            "owner_id": record.owner_id,
            "receipt_id": record.receipt_id,
            "result_reference": record.result_reference,
        }
        if extra:
            payload.update(extra)
        tmp = self._op_path(record.key.operation_id).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        tmp.replace(self._op_path(record.key.operation_id))

    def _to_record(self, raw: dict) -> DistributedOperationRecord:
        key = DistributedOperationKey(**raw["key"])
        return DistributedOperationRecord(
            key=key,
            state=DistributedOperationState(raw["state"]),
            owner_id=raw.get("owner_id"),
            receipt_id=raw.get("receipt_id"),
            result_reference=raw.get("result_reference"),
        )

    def read(self, key: DistributedOperationKey) -> DistributedOperationRecord | None:
        raw = self._load_raw(key.operation_id)
        if raw is None:
            return None
        record = self._to_record(raw)
        validate_replay(
            record,
            operation_id=key.operation_id,
            payload_fingerprint=key.payload_fingerprint,
        )
        return record

    def read_by_operation(self, operation_id: str) -> DistributedOperationRecord | None:
        raw = self._load_raw(operation_id)
        return None if raw is None else self._to_record(raw)

    def claim(self, key: DistributedOperationKey, owner_id: str) -> DistributedOperationRecord:
        handle = self._lock_fd(key.operation_id)
        try:
            existing = self.read_by_operation(key.operation_id)
            if existing is not None:
                validate_replay(
                    existing,
                    operation_id=key.operation_id,
                    payload_fingerprint=key.payload_fingerprint,
                )
                if existing.state in {
                    DistributedOperationState.SUCCEEDED,
                    DistributedOperationState.FAILED,
                    DistributedOperationState.RECONCILED,
                    DistributedOperationState.HOLD,
                }:
                    return existing
                lease = self._read_lease(key.operation_id)
                if lease and not lease.is_expired() and lease.owner_id != owner_id:
                    raise LeaseConflict("active_owner_exists")
            fencing = 1
            lease = self._read_lease(key.operation_id)
            if lease:
                fencing = lease.fencing_token + 1
            record = DistributedOperationRecord(
                key=key,
                state=DistributedOperationState.EXECUTING,
                owner_id=owner_id,
            )
            self._dump(record, extra={"fencing_token": fencing})
            self._write_lease(key.operation_id, owner_id, fencing)
            return record
        finally:
            handle.close()

    def write(self, record: DistributedOperationRecord) -> DistributedOperationRecord:
        handle = self._lock_fd(record.key.operation_id)
        try:
            existing = self.read_by_operation(record.key.operation_id)
            if existing is None:
                raise LeaseConflict("cannot_write_absent_operation")
            if existing.owner_id and record.owner_id != existing.owner_id:
                lease = self._read_lease(record.key.operation_id)
                if lease and not lease.is_expired() and lease.owner_id != record.owner_id:
                    raise StaleOwner("stale owner cannot overwrite")
            if existing.state in {
                DistributedOperationState.SUCCEEDED,
                DistributedOperationState.RECONCILED,
            } and record.state == DistributedOperationState.SUCCEEDED:
                return existing
            if record.state == DistributedOperationState.SUCCEEDED and not record.receipt_id:
                raise LeaseConflict("success_requires_receipt")
            self._dump(record)
            return record
        finally:
            handle.close()

    def put_receipt(self, receipt_id: str, payload: dict) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = sha256(blob.encode()).hexdigest()
        path = self.root / "receipts" / f"{receipt_id}.json"
        path.write_text(blob, encoding="utf-8")
        return digest

    def get_receipt(self, receipt_id: str) -> dict | None:
        path = self.root / "receipts" / f"{receipt_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LeaseConflict("corrupt_receipt") from exc

    def recover(self, operation_id: str, *, owner_id: str) -> RecoveryReceipt:
        record = self.read_by_operation(operation_id)
        if record is None:
            return reconcile_receipt(
                operation_id=operation_id,
                decision=RecoveryDecision.HOLD.value,
                observed_state=DistributedOperationState.ABSENT.value,
                effect_observed=None,
                evidence_reference=None,
            )
        receipt_readable = False
        effect_observed: bool | None = None
        if record.receipt_id:
            try:
                receipt = self.get_receipt(record.receipt_id)
                receipt_readable = receipt is not None
                if receipt_readable:
                    effect_observed = True
            except LeaseConflict:
                receipt_readable = False
                effect_observed = None
        elif record.state == DistributedOperationState.EXECUTING:
            effect_observed = False
        observation = RecoveryObservation(
            operation_id=operation_id,
            state=record.state.value,
            effect_observed=effect_observed,
            idempotency_verified=True,
            receipt_readable=receipt_readable,
        )
        decision = decide_recovery(observation)
        evidence = record.receipt_id if decision is RecoveryDecision.RECONCILE else None
        if decision is RecoveryDecision.HOLD:
            held = DistributedOperationRecord(
                key=record.key,
                state=DistributedOperationState.HOLD,
                owner_id=owner_id,
                receipt_id=record.receipt_id,
                result_reference=record.result_reference,
            )
            try:
                self.write(held)
            except StaleOwner:
                pass
        elif decision is RecoveryDecision.RECONCILE:
            reconciled = DistributedOperationRecord(
                key=record.key,
                state=DistributedOperationState.RECONCILED,
                owner_id=record.owner_id,
                receipt_id=record.receipt_id,
                result_reference=record.result_reference,
            )
            self.write(reconciled)
        return reconcile_receipt(
            operation_id=operation_id,
            decision=decision.value,
            observed_state=record.state.value,
            effect_observed=effect_observed,
            evidence_reference=evidence,
        )

    def _read_lease(self, operation_id: str) -> Lease | None:
        path = self._lease_path(operation_id)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Lease(
            owner_id=raw["owner_id"],
            operation_id=operation_id,
            fencing_token=int(raw["fencing_token"]),
            expires_at=datetime.fromisoformat(raw["expires_at"]),
        )

    def _write_lease(self, operation_id: str, owner_id: str, fencing: int) -> None:
        expires = datetime.now(timezone.utc) + timedelta(seconds=LEASE_SECONDS)
        payload = {
            "owner_id": owner_id,
            "fencing_token": fencing,
            "expires_at": expires.isoformat(),
        }
        self._lease_path(operation_id).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def expire_lease(self, operation_id: str) -> None:
        path = self._lease_path(operation_id)
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
