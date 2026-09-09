from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.noesis_r7.contracts import (
    CommandStatus,
    CommunicationEnvelope,
    GovernorContract,
    GovernorFunction,
    GovernorLease,
    GovernanceCommand,
    GovernanceReceipt,
    GovernanceTask,
    LeaseStatus,
    R7InvariantError,
    RecoveryCheckpoint,
)
from app.noesis_r7.integration import R1R6IntegrationContract
from app.noesis_r7.runtime import R7GovernanceRuntime


class R7DurableRuntime(R7GovernanceRuntime):
    """Restart-safe R7 runtime with append-only SQLite snapshot journal.

    SQLite is an engineering persistence substrate for this candidate only. It is
    not a source of institutional identity or authority and does not replace L0/R1-R6.
    """

    def __init__(
        self,
        *,
        mission_id: str,
        integration: R1R6IntegrationContract,
        database_path: Path,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self._database_path = database_path
        self._persistence_suspended = False
        self._durable_head_hash = "GENESIS"
        self._initialize_database()
        super().__init__(
            mission_id=mission_id,
            integration=integration,
            initial_state=initial_state,
        )
        loaded = self._load_latest_snapshot()
        if loaded is None:
            self._persist_snapshot("INITIALIZE")
        else:
            payload, snapshot_hash = loaded
            self._restore_snapshot(payload)
            self._durable_head_hash = snapshot_hash

    @staticmethod
    def _snapshot_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS r7_runtime_snapshot_journal (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    state_version INTEGER NOT NULL,
                    predecessor_hash TEXT NOT NULL,
                    snapshot_hash TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_r7_snapshot_mission_seq
                ON r7_runtime_snapshot_journal (mission_id, seq)
                """
            )

    def register_governor(self, contract: GovernorContract) -> None:
        super().register_governor(contract)
        self._persist_if_enabled("REGISTER_GOVERNOR")

    def bind_lease(self, lease: GovernorLease) -> None:
        super().bind_lease(lease)
        self._persist_if_enabled("BIND_LEASE")

    def fence_generation(self, governor_id: str) -> int:
        generation = super().fence_generation(governor_id)
        self._persist_if_enabled("FENCE_GENERATION")
        return generation

    def schedule(self, task: GovernanceTask) -> None:
        super().schedule(task)
        self._persist_if_enabled("SCHEDULE_TASK")

    def next_task(self) -> GovernanceTask | None:
        task = super().next_task()
        if task is not None:
            self._persist_if_enabled("DEQUEUE_TASK")
        return task

    def communicate(self, envelope: CommunicationEnvelope) -> None:
        super().communicate(envelope)
        self._persist_if_enabled("COMMUNICATE")

    def execute(
        self,
        command: GovernanceCommand,
        *,
        now: float,
    ) -> GovernanceReceipt:
        try:
            receipt = super().execute(command, now=now)
        except RuntimeError as exc:
            if str(exc).startswith("injected_failure_after_commit:"):
                self._persist_snapshot("POST_COMMIT_FAILURE_RECOVERY_POINT")
            raise
        self._persist_snapshot("EXECUTE_COMMAND")
        return receipt

    def checkpoint(
        self,
        checkpoint_id: str,
        *,
        now: float,
    ) -> RecoveryCheckpoint:
        checkpoint = super().checkpoint(checkpoint_id, now=now)
        self._persist_snapshot("CHECKPOINT")
        return checkpoint

    def recover_governor(
        self,
        governor_id: str,
        *,
        checkpoint_id: str,
    ) -> int:
        self._persistence_suspended = True
        try:
            generation = super().recover_governor(
                governor_id,
                checkpoint_id=checkpoint_id,
            )
        finally:
            self._persistence_suspended = False
        self._persist_snapshot("RECOVER_GOVERNOR")
        return generation

    def rollback_to_checkpoint(self, checkpoint_id: str) -> None:
        self._persistence_suspended = True
        try:
            super().rollback_to_checkpoint(checkpoint_id)
        finally:
            self._persistence_suspended = False
        self._persist_snapshot("ROLLBACK_TO_CHECKPOINT")

    def _persist_if_enabled(self, reason: str) -> None:
        if not self._persistence_suspended:
            self._persist_snapshot(reason)

    def _snapshot(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "state": self._state,
            "state_version": self._state_version,
            "governors": [asdict(value) for value in self._governors.values()],
            "leases": [asdict(value) for value in self._leases.values()],
            "generation_by_governor": self._generation_by_governor,
            "tasks": [asdict(value) for value in self._tasks],
            "task_seq": self._task_seq,
            "receipts": [asdict(value) for value in self._receipts],
            "idempotency": {
                key: {
                    "fingerprint": fingerprint,
                    "receipt_id": receipt.receipt_id,
                }
                for key, (fingerprint, receipt) in self._idempotency.items()
            },
            "invalidated_idempotency": sorted(self._invalidated_idempotency),
            "communications": [asdict(value) for value in self._communications],
            "checkpoints": [asdict(value) for value in self._checkpoints.values()],
        }

    def _persist_snapshot(self, reason: str) -> None:
        payload = self._snapshot()
        snapshot_hash = self._snapshot_hash(payload)
        serialized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT snapshot_hash, snapshot_json
                FROM r7_runtime_snapshot_journal
                WHERE mission_id = ?
                ORDER BY seq DESC
                LIMIT 1
                """,
                (self.mission_id,),
            ).fetchone()
            actual_head = str(row["snapshot_hash"]) if row else "GENESIS"
            if actual_head != self._durable_head_hash:
                connection.rollback()
                if row is not None:
                    latest_payload = json.loads(str(row["snapshot_json"]))
                    if self._snapshot_hash(latest_payload) != actual_head:
                        raise R7InvariantError(
                            "R7_DURABLE_SNAPSHOT_INTEGRITY_FAILURE"
                        )
                    self._restore_snapshot(latest_payload)
                    self._durable_head_hash = actual_head
                raise R7InvariantError("R7_DURABLE_STALE_WRITER")
            connection.execute(
                """
                INSERT INTO r7_runtime_snapshot_journal (
                    mission_id,
                    reason,
                    state_version,
                    predecessor_hash,
                    snapshot_hash,
                    snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.mission_id,
                    reason,
                    self._state_version,
                    actual_head,
                    snapshot_hash,
                    serialized,
                ),
            )
            connection.commit()
            self._durable_head_hash = snapshot_hash
        finally:
            connection.close()

    def _load_latest_snapshot(self) -> tuple[dict[str, Any], str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json, snapshot_hash
                FROM r7_runtime_snapshot_journal
                WHERE mission_id = ?
                ORDER BY seq DESC
                LIMIT 1
                """,
                (self.mission_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(str(row["snapshot_json"]))
        snapshot_hash = str(row["snapshot_hash"])
        if self._snapshot_hash(payload) != snapshot_hash:
            raise R7InvariantError("R7_DURABLE_SNAPSHOT_INTEGRITY_FAILURE")
        return payload, snapshot_hash

    def verify_snapshot_chain(self) -> bool:
        previous = "GENESIS"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT predecessor_hash, snapshot_hash, snapshot_json
                FROM r7_runtime_snapshot_journal
                WHERE mission_id = ?
                ORDER BY seq ASC
                """,
                (self.mission_id,),
            ).fetchall()
        for row in rows:
            if str(row["predecessor_hash"]) != previous:
                return False
            payload = json.loads(str(row["snapshot_json"]))
            snapshot_hash = str(row["snapshot_hash"])
            if self._snapshot_hash(payload) != snapshot_hash:
                return False
            previous = snapshot_hash
        return True

    def _restore_snapshot(self, payload: dict[str, Any]) -> None:
        if payload.get("mission_id") != self.mission_id:
            raise R7InvariantError("R7_DURABLE_MISSION_MISMATCH")
        self._state = dict(payload["state"])
        self._state_version = int(payload["state_version"])
        self._governors = {}
        for raw in payload["governors"]:
            contract = GovernorContract(
                governor_id=str(raw["governor_id"]),
                function=GovernorFunction(str(raw["function"])),
                owned_state_keys=tuple(raw["owned_state_keys"]),
                readable_state_keys=tuple(raw["readable_state_keys"]),
                allowed_commands=tuple(raw["allowed_commands"]),
                authority_ceiling_ref=str(raw["authority_ceiling_ref"]),
                lease_required=bool(raw["lease_required"]),
                recovery_policy=str(raw["recovery_policy"]),
            )
            self._governors[contract.governor_id] = contract
        self._leases = {}
        for raw in payload["leases"]:
            lease = GovernorLease(
                lease_id=str(raw["lease_id"]),
                governor_id=str(raw["governor_id"]),
                mission_id=str(raw["mission_id"]),
                authority_ref=str(raw["authority_ref"]),
                authority_source_ref=str(raw["authority_source_ref"]),
                scope=tuple(raw["scope"]),
                generation=int(raw["generation"]),
                issued_at=float(raw["issued_at"]),
                not_before=float(raw["not_before"]),
                expires_at=float(raw["expires_at"]),
                max_uses=int(raw["max_uses"]),
                uses=int(raw["uses"]),
                status=LeaseStatus(str(raw["status"])),
            )
            self._leases[lease.lease_id] = lease
        self._generation_by_governor = {
            str(key): int(value)
            for key, value in payload["generation_by_governor"].items()
        }
        self._tasks = [
            GovernanceTask(
                task_id=str(raw["task_id"]),
                mission_id=str(raw["mission_id"]),
                governor_id=str(raw["governor_id"]),
                command_type=str(raw["command_type"]),
                priority=int(raw["priority"]),
                created_seq=int(raw["created_seq"]),
            )
            for raw in payload["tasks"]
        ]
        self._task_seq = int(payload["task_seq"])
        self._receipts = [
            GovernanceReceipt(
                receipt_id=str(raw["receipt_id"]),
                command_id=str(raw["command_id"]),
                governor_id=str(raw["governor_id"]),
                idempotency_key=str(raw["idempotency_key"]),
                status=CommandStatus(str(raw["status"])),
                reason=str(raw["reason"]),
                generation=int(raw["generation"]),
                state_version_before=int(raw["state_version_before"]),
                state_version_after=int(raw["state_version_after"]),
                mutation_count=int(raw["mutation_count"]),
                material_effect_performed=bool(raw["material_effect_performed"]),
                previous_hash=str(raw["previous_hash"]),
                receipt_hash=str(raw["receipt_hash"]),
                readback=dict(raw["readback"]),
            )
            for raw in payload["receipts"]
        ]
        receipt_by_id = {receipt.receipt_id: receipt for receipt in self._receipts}
        self._idempotency = {
            str(key): (
                str(value["fingerprint"]),
                receipt_by_id[str(value["receipt_id"])],
            )
            for key, value in payload["idempotency"].items()
        }
        self._invalidated_idempotency = set(payload["invalidated_idempotency"])
        self._communications = [
            CommunicationEnvelope(
                message_id=str(raw["message_id"]),
                mission_id=str(raw["mission_id"]),
                source_governor_id=str(raw["source_governor_id"]),
                target_governor_id=str(raw["target_governor_id"]),
                relation=str(raw["relation"]),
                payload_ref=str(raw["payload_ref"]),
                authority_transferred=bool(raw["authority_transferred"]),
            )
            for raw in payload["communications"]
        ]
        self._checkpoints = {}
        for raw in payload["checkpoints"]:
            checkpoint = RecoveryCheckpoint(
                checkpoint_id=str(raw["checkpoint_id"]),
                mission_id=str(raw["mission_id"]),
                generation_snapshot={
                    str(key): int(value)
                    for key, value in raw["generation_snapshot"].items()
                },
                state_version=int(raw["state_version"]),
                state=dict(raw["state"]),
                predecessor_receipt_hash=str(raw["predecessor_receipt_hash"]),
                receipt_count=int(raw["receipt_count"]),
                created_at=float(raw["created_at"]),
            )
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        if not self.verify_receipt_chain():
            raise R7InvariantError("R7_DURABLE_RECEIPT_CHAIN_INVALID")
