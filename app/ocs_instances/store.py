from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from pathlib import Path
from threading import RLock
from time import time
from typing import Any

from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
    require_transition,
)


class InstanceBindingStore:
    """Durable instance registry with optimistic concurrency and a journal."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ocs_instance_bindings (
                    binding_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    ocs_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    profile_hash TEXT NOT NULL,
                    identity_binding_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    maturity TEXT NOT NULL,
                    host TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    authority_ref TEXT NOT NULL,
                    scope_json TEXT NOT NULL,
                    state_namespace TEXT NOT NULL,
                    memory_namespace TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    platform_instance_id TEXT,
                    challenge_hash TEXT NOT NULL,
                    bootstrap_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    predecessor_binding_id TEXT,
                    checkpoint_version INTEGER NOT NULL,
                    checkpoint_hash TEXT,
                    hazel_event_hash TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    correlation_id TEXT NOT NULL,
                    causation_id TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(organization_id, mission_id, ocs_id, generation),
                    UNIQUE(platform_instance_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ocs_instance_journal (
                    position INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    binding_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    binding_version INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    occurred_at REAL NOT NULL,
                    FOREIGN KEY(binding_id) REFERENCES ocs_instance_bindings(binding_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ocs_action_sagas (
                    idempotency_key TEXT PRIMARY KEY,
                    binding_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(binding_id) REFERENCES ocs_instance_bindings(binding_id)
                )
                """
            )

    def create(self, binding: InstanceBinding) -> InstanceBinding:
        if binding.status is not InstanceStatus.PREPARED or binding.version != 1:
            raise InstanceBindingError("instance_initial_state_invalid")
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE idempotency_key = ?",
                (binding.idempotency_key,),
            ).fetchone()
            if existing is not None:
                recovered = self._row(existing)
                if recovered.request_hash != binding.request_hash:
                    raise InstanceBindingError("instance_idempotency_conflict")
                return recovered
            active = connection.execute(
                """
                SELECT binding_id FROM ocs_instance_bindings
                WHERE organization_id = ? AND mission_id = ? AND ocs_id = ?
                  AND status IN (
                    'prepared', 'persisted', 'bound', 'active', 'checkpointed'
                  )
                """,
                (binding.organization_id, binding.mission_id, binding.ocs_id),
            ).fetchone()
            if active is not None and binding.predecessor_binding_id is None:
                raise InstanceBindingError("active_mission_ocs_binding_exists")
            if binding.predecessor_binding_id is not None:
                predecessor_row = connection.execute(
                    "SELECT * FROM ocs_instance_bindings WHERE binding_id = ?",
                    (binding.predecessor_binding_id,),
                ).fetchone()
                if predecessor_row is None:
                    raise InstanceBindingError("replacement_predecessor_not_found")
                predecessor = self._row(predecessor_row)
                if (
                    predecessor.status is not InstanceStatus.CHECKPOINTED
                    or binding.organization_id != predecessor.organization_id
                    or binding.mission_id != predecessor.mission_id
                    or binding.ocs_id != predecessor.ocs_id
                    or binding.run_id != predecessor.run_id
                    or binding.generation != predecessor.generation + 1
                ):
                    raise InstanceBindingError("replacement_lineage_mismatch")
            values = self._values(binding)
            connection.execute(
                """
                INSERT INTO ocs_instance_bindings (
                    binding_id, mission_id, run_id, organization_id, ocs_id,
                    profile_version, profile_hash, identity_binding_hash,
                    request_hash, maturity, host, capability, lease_id,
                    authority_ref, scope_json, state_namespace, memory_namespace,
                    generation, platform_instance_id, challenge_hash, bootstrap_hash,
                    status, version, predecessor_binding_id, checkpoint_version,
                    checkpoint_hash, hazel_event_hash, idempotency_key,
                    correlation_id, causation_id,
                    created_at, updated_at
                ) VALUES (
                    :binding_id, :mission_id, :run_id, :organization_id, :ocs_id,
                    :profile_version, :profile_hash, :identity_binding_hash,
                    :request_hash, :maturity, :host, :capability, :lease_id,
                    :authority_ref, :scope_json, :state_namespace, :memory_namespace,
                    :generation, :platform_instance_id, :challenge_hash,
                    :bootstrap_hash,
                    :status, :version, :predecessor_binding_id, :checkpoint_version,
                    :checkpoint_hash, :hazel_event_hash, :idempotency_key,
                    :correlation_id, :causation_id,
                    :created_at, :updated_at
                )
                """,
                values,
            )
            self._append_event(
                connection,
                binding=binding,
                event_type="OCS_INSTANCE_PREPARED",
                from_status=None,
                idempotency_key=f"{binding.idempotency_key}:prepared",
                payload={"profile_hash": binding.profile_hash},
            )
        return binding

    def by_idempotency(self, idempotency_key: str) -> InstanceBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return None if row is None else self._row(row)

    def get(self, binding_id: str) -> InstanceBinding:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        if row is None:
            raise InstanceBindingError("instance_binding_not_found")
        return self._row(row)

    def latest_generation(
        self, organization_id: str, mission_id: str, ocs_id: str
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(generation) AS generation FROM ocs_instance_bindings
                WHERE organization_id = ? AND mission_id = ? AND ocs_id = ?
                """,
                (organization_id, mission_id, ocs_id),
            ).fetchone()
        value = None if row is None else row["generation"]
        return 0 if value is None else int(value)

    def transition(
        self,
        binding_id: str,
        *,
        expected_version: int,
        target: InstanceStatus,
        idempotency_key: str,
        event_type: str,
        platform_instance_id: str | None = None,
        checkpoint_version: int | None = None,
        checkpoint_hash: str | None = None,
        hazel_event_hash: str | None = None,
        maturity: BindingMaturity | None = None,
        payload: dict[str, Any] | None = None,
    ) -> InstanceBinding:
        with self._lock, self._connect() as connection:
            replay = connection.execute(
                "SELECT * FROM ocs_instance_journal WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            requested_payload = {
                **({} if payload is None else payload),
                "platform_instance_id": platform_instance_id,
                "checkpoint_version": checkpoint_version,
                "checkpoint_hash": checkpoint_hash,
                "hazel_event_hash": hazel_event_hash,
                "maturity": None if maturity is None else maturity.value,
            }
            requested_hash = json.dumps(
                requested_payload, sort_keys=True, separators=(",", ":")
            )
            if replay is not None:
                if (
                    replay["binding_id"] != binding_id
                    or replay["event_type"] != event_type
                    or replay["to_status"] != target.value
                    or replay["payload_json"] != requested_hash
                ):
                    raise InstanceBindingError("instance_idempotency_conflict")
                return self.get(binding_id)
            row = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
            if row is None:
                raise InstanceBindingError("instance_binding_not_found")
            current = self._row(row)
            if current.version != expected_version:
                raise InstanceBindingError("instance_version_conflict")
            require_transition(current.status, target)
            updated = replace(
                current,
                status=target,
                version=current.version + 1,
                platform_instance_id=(
                    current.platform_instance_id
                    if platform_instance_id is None
                    else platform_instance_id
                ),
                checkpoint_version=(
                    current.checkpoint_version
                    if checkpoint_version is None
                    else checkpoint_version
                ),
                checkpoint_hash=(
                    current.checkpoint_hash
                    if checkpoint_hash is None
                    else checkpoint_hash
                ),
                maturity=current.maturity if maturity is None else maturity,
                hazel_event_hash=(
                    current.hazel_event_hash
                    if hazel_event_hash is None
                    else hazel_event_hash
                ),
                updated_at=time(),
            )
            cursor = connection.execute(
                """
                UPDATE ocs_instance_bindings
                SET status = ?, version = ?, maturity = ?, platform_instance_id = ?,
                    checkpoint_version = ?, checkpoint_hash = ?,
                    hazel_event_hash = ?, updated_at = ?
                WHERE binding_id = ? AND version = ?
                """,
                (
                    updated.status.value,
                    updated.version,
                    updated.maturity.value,
                    updated.platform_instance_id,
                    updated.checkpoint_version,
                    updated.checkpoint_hash,
                    updated.hazel_event_hash,
                    updated.updated_at,
                    binding_id,
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                raise InstanceBindingError("instance_version_conflict")
            self._append_event(
                connection,
                binding=updated,
                event_type=event_type,
                from_status=current.status,
                idempotency_key=idempotency_key,
                payload=requested_payload,
            )
        return updated

    def commit_replacement(
        self,
        *,
        predecessor_id: str,
        predecessor_expected_version: int,
        successor_id: str,
        successor_expected_version: int,
        idempotency_key: str,
        checkpoint_version: int,
        checkpoint_hash: str,
        hazel_event_hash: str,
    ) -> tuple[InstanceBinding, InstanceBinding]:
        with self._lock, self._connect() as connection:
            replay_payload = {
                "successor_binding_id": successor_id,
                "predecessor_expected_version": predecessor_expected_version,
                "successor_expected_version": successor_expected_version,
                "checkpoint_version": checkpoint_version,
                "checkpoint_hash": checkpoint_hash,
                "hazel_event_hash": hazel_event_hash,
            }
            replay_hash = json.dumps(
                replay_payload, sort_keys=True, separators=(",", ":")
            )
            replay = connection.execute(
                "SELECT * FROM ocs_instance_journal WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if replay is not None:
                if (
                    replay["binding_id"] != predecessor_id
                    or replay["event_type"] != "OCS_INSTANCE_REPLACED"
                    or replay["to_status"] != InstanceStatus.REPLACED.value
                    or replay["payload_json"] != replay_hash
                ):
                    raise InstanceBindingError("instance_idempotency_conflict")
                return self.get(predecessor_id), self.get(successor_id)
            predecessor_row = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE binding_id = ?",
                (predecessor_id,),
            ).fetchone()
            successor_row = connection.execute(
                "SELECT * FROM ocs_instance_bindings WHERE binding_id = ?",
                (successor_id,),
            ).fetchone()
            if predecessor_row is None or successor_row is None:
                raise InstanceBindingError("replacement_binding_not_found")
            predecessor = self._row(predecessor_row)
            successor = self._row(successor_row)
            if (
                successor.predecessor_binding_id != predecessor.binding_id
                or successor.organization_id != predecessor.organization_id
                or successor.mission_id != predecessor.mission_id
                or successor.ocs_id != predecessor.ocs_id
                or successor.run_id != predecessor.run_id
                or successor.generation != predecessor.generation + 1
            ):
                raise InstanceBindingError("replacement_lineage_mismatch")
            if (
                predecessor.version != predecessor_expected_version
                or successor.version != successor_expected_version
            ):
                raise InstanceBindingError("instance_version_conflict")
            if predecessor.status is not InstanceStatus.CHECKPOINTED:
                raise InstanceBindingError(
                    "verified_checkpoint_required_for_replacement"
                )
            if successor.status is not InstanceStatus.PREPARED:
                raise InstanceBindingError("replacement_successor_not_prepared")
            now = time()
            replaced = replace(
                predecessor,
                status=InstanceStatus.REPLACED,
                version=predecessor.version + 1,
                updated_at=now,
            )
            persisted = replace(
                successor,
                status=InstanceStatus.PERSISTED,
                version=successor.version + 1,
                checkpoint_version=checkpoint_version,
                checkpoint_hash=checkpoint_hash,
                hazel_event_hash=hazel_event_hash,
                updated_at=now,
            )
            first = connection.execute(
                """
                UPDATE ocs_instance_bindings
                SET status = ?, version = ?, updated_at = ?
                WHERE binding_id = ? AND version = ?
                """,
                (
                    replaced.status.value,
                    replaced.version,
                    now,
                    predecessor_id,
                    predecessor_expected_version,
                ),
            )
            second = connection.execute(
                """
                UPDATE ocs_instance_bindings
                SET status = ?, version = ?, checkpoint_version = ?,
                    checkpoint_hash = ?, hazel_event_hash = ?, updated_at = ?
                WHERE binding_id = ? AND version = ?
                """,
                (
                    persisted.status.value,
                    persisted.version,
                    persisted.checkpoint_version,
                    persisted.checkpoint_hash,
                    persisted.hazel_event_hash,
                    now,
                    successor_id,
                    successor_expected_version,
                ),
            )
            if first.rowcount != 1 or second.rowcount != 1:
                raise InstanceBindingError("instance_version_conflict")
            self._append_event(
                connection,
                binding=replaced,
                event_type="OCS_INSTANCE_REPLACED",
                from_status=predecessor.status,
                idempotency_key=idempotency_key,
                payload=replay_payload,
            )
            self._append_event(
                connection,
                binding=persisted,
                event_type="OCS_REPLACEMENT_PERSISTED",
                from_status=successor.status,
                idempotency_key=f"{idempotency_key}:successor",
                payload={
                    "predecessor_binding_id": predecessor_id,
                    "state_version": checkpoint_version,
                },
            )
        return replaced, persisted

    def journal(self, binding_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM ocs_instance_journal
                WHERE binding_id = ? ORDER BY position
                """,
                (binding_id,),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def transition_replay(
        self,
        *,
        binding_id: str,
        target: InstanceStatus,
        idempotency_key: str,
        event_type: str,
        platform_instance_id: str | None = None,
        checkpoint_version: int | None = None,
        checkpoint_hash: str | None = None,
        hazel_event_hash: str | None = None,
        maturity: BindingMaturity | None = None,
        payload: dict[str, Any] | None = None,
    ) -> InstanceBinding | None:
        requested_payload = {
            **({} if payload is None else payload),
            "platform_instance_id": platform_instance_id,
            "checkpoint_version": checkpoint_version,
            "checkpoint_hash": checkpoint_hash,
            "hazel_event_hash": hazel_event_hash,
            "maturity": None if maturity is None else maturity.value,
        }
        requested_hash = json.dumps(
            requested_payload, sort_keys=True, separators=(",", ":")
        )
        with self._connect() as connection:
            replay = connection.execute(
                "SELECT * FROM ocs_instance_journal WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if replay is None:
            return None
        if (
            replay["binding_id"] != binding_id
            or replay["event_type"] != event_type
            or replay["to_status"] != target.value
            or replay["payload_json"] != requested_hash
        ):
            raise InstanceBindingError("instance_idempotency_conflict")
        return self.get(binding_id)

    def checkpoint_replay(
        self,
        *,
        binding_id: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> InstanceBinding | None:
        with self._connect() as connection:
            replay = connection.execute(
                "SELECT * FROM ocs_instance_journal WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if replay is None:
            return None
        payload = json.loads(str(replay["payload_json"]))
        if (
            replay["binding_id"] != binding_id
            or replay["event_type"] != "OCS_INSTANCE_CHECKPOINTED"
            or replay["to_status"] != InstanceStatus.CHECKPOINTED.value
            or payload.get("request_fingerprint") != request_fingerprint
        ):
            raise InstanceBindingError("instance_idempotency_conflict")
        return self.get(binding_id)

    def begin_action_saga(
        self,
        *,
        idempotency_key: str,
        binding_id: str,
        operation: str,
        request_fingerprint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ocs_action_sagas WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is not None:
                current = dict(row)
                if (
                    current["binding_id"] != binding_id
                    or current["operation"] != operation
                    or current["request_fingerprint"] != request_fingerprint
                    or current["payload_json"] != payload_json
                ):
                    raise InstanceBindingError("instance_idempotency_conflict")
                return current
            connection.execute(
                """
                INSERT INTO ocs_action_sagas (
                    idempotency_key, binding_id, operation, request_fingerprint,
                    state, payload_json, updated_at
                ) VALUES (?, ?, ?, ?, 'LEASE_RESERVED', ?, ?)
                """,
                (
                    idempotency_key,
                    binding_id,
                    operation,
                    request_fingerprint,
                    payload_json,
                    time(),
                ),
            )
        return self.action_saga(idempotency_key)

    def action_saga(self, idempotency_key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ocs_action_sagas WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            raise InstanceBindingError("action_saga_not_found")
        return dict(row)

    def advance_action_saga(
        self,
        idempotency_key: str,
        *,
        expected_state: str,
        target_state: str,
    ) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ocs_action_sagas SET state = ?, updated_at = ?
                WHERE idempotency_key = ? AND state = ?
                """,
                (target_state, time(), idempotency_key, expected_state),
            )
            if cursor.rowcount != 1:
                row = connection.execute(
                    "SELECT state FROM ocs_action_sagas WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is None or row["state"] != target_state:
                    raise InstanceBindingError("action_saga_state_conflict")
        return self.action_saga(idempotency_key)

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        *,
        binding: InstanceBinding,
        event_type: str,
        from_status: InstanceStatus | None,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO ocs_instance_journal (
                event_id, binding_id, event_type, from_status, to_status,
                binding_version, idempotency_key, payload_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{binding.binding_id}:{binding.version}:{event_type}",
                binding.binding_id,
                event_type,
                None if from_status is None else from_status.value,
                binding.status.value,
                binding.version,
                idempotency_key,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                binding.updated_at,
            ),
        )

    @staticmethod
    def _values(binding: InstanceBinding) -> dict[str, Any]:
        values = asdict(binding)
        values["status"] = binding.status.value
        values["maturity"] = binding.maturity.value
        values["scope_json"] = json.dumps(binding.scope)
        values.pop("scope")
        return values

    @staticmethod
    def _row(row: sqlite3.Row) -> InstanceBinding:
        return InstanceBinding(
            binding_id=str(row["binding_id"]),
            mission_id=str(row["mission_id"]),
            run_id=str(row["run_id"]),
            organization_id=str(row["organization_id"]),
            ocs_id=str(row["ocs_id"]),
            profile_version=str(row["profile_version"]),
            profile_hash=str(row["profile_hash"]),
            identity_binding_hash=str(row["identity_binding_hash"]),
            request_hash=str(row["request_hash"]),
            maturity=BindingMaturity(str(row["maturity"])),
            host=str(row["host"]),
            capability=str(row["capability"]),
            lease_id=str(row["lease_id"]),
            authority_ref=str(row["authority_ref"]),
            scope=tuple(str(item) for item in json.loads(row["scope_json"])),
            state_namespace=str(row["state_namespace"]),
            memory_namespace=str(row["memory_namespace"]),
            generation=int(row["generation"]),
            platform_instance_id=row["platform_instance_id"],
            challenge_hash=str(row["challenge_hash"]),
            bootstrap_hash=str(row["bootstrap_hash"]),
            status=InstanceStatus(str(row["status"])),
            version=int(row["version"]),
            predecessor_binding_id=row["predecessor_binding_id"],
            checkpoint_version=int(row["checkpoint_version"]),
            checkpoint_hash=row["checkpoint_hash"],
            hazel_event_hash=row["hazel_event_hash"],
            idempotency_key=str(row["idempotency_key"]),
            correlation_id=str(row["correlation_id"]),
            causation_id=row["causation_id"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
