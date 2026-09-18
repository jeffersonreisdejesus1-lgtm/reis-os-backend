from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from app.iris_v1.contracts import (
    DecisionStatus,
    GovernorLease,
    GovernorSpec,
    GovernanceReceipt,
    IRIS_DERIVATION_REF,
    IRIS_DESIGN_AUTHORITY,
    IRIS_IDENTITY_STATE_ROOT,
    IrisV1Bindings,
    IrisV1InvariantError,
    RecoveryCheckpoint,
)
from app.iris_v1.runtime import (
    GOVERNOR_WRITABLE_NAMESPACE,
    NAMESPACE_OWNERS,
    IrisV1Runtime,
    derived_governor_specs,
)


class IrisV1DurableRuntime(IrisV1Runtime):
    """Restart-safe local Íris V1 candidate with append-only SQLite snapshots."""

    def __init__(
        self,
        *,
        mission_id: str,
        bindings: IrisV1Bindings,
        derivation_ref: str,
        database_path: Path,
    ) -> None:
        self._database_path = Path(database_path)
        self._persistence_suspended = True
        self._durable_head_hash = "GENESIS"
        self._initialize_database()
        super().__init__(mission_id=mission_id, bindings=bindings, derivation_ref=derivation_ref)
        loaded = self._load_latest_snapshot()
        if loaded is None:
            self._persistence_suspended = False
            self._persist_snapshot("INITIALIZE")
        else:
            payload, snapshot_hash = loaded
            self._restore_snapshot(payload)
            self._durable_head_hash = snapshot_hash
            self._persistence_suspended = False

    def register_governor(self, spec: GovernorSpec) -> None:
        super().register_governor(spec)
        self._persist_if_enabled("REGISTER_GOVERNOR")

    def bind_lease(self, lease: GovernorLease) -> None:
        super().bind_lease(lease)
        self._persist_if_enabled("BIND_LEASE")

    def fence_generation(self, governor_id: str) -> int:
        generation = super().fence_generation(governor_id)
        self._persist_if_enabled("FENCE_GENERATION")
        return generation

    def execute(self, request, *, now: float):
        receipt = super().execute(request, now=now)
        if receipt.status is DecisionStatus.ACCEPTED and not receipt.idempotent_replay:
            self._persist_snapshot("EXECUTE")
        return receipt

    def checkpoint(self, checkpoint_id: str, *, governor_id: str) -> RecoveryCheckpoint:
        checkpoint = super().checkpoint(checkpoint_id, governor_id=governor_id)
        self._persist_if_enabled("CHECKPOINT")
        return checkpoint

    def recover_governor(self, governor_id: str, *, checkpoint_id: str) -> int:
        self._persistence_suspended = True
        try:
            generation = super().recover_governor(governor_id, checkpoint_id=checkpoint_id)
        finally:
            self._persistence_suspended = False
        self._persist_snapshot("RECOVER_GOVERNOR")
        return generation

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS iris_v1_snapshot_journal (
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
                "CREATE INDEX IF NOT EXISTS ix_iris_v1_snapshot_mission_seq "
                "ON iris_v1_snapshot_journal (mission_id, seq)"
            )

    @staticmethod
    def _snapshot_hash(payload: dict[str, object]) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(raw).hexdigest()

    def _snapshot(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "identity_state_root": self.identity_state_root,
            "design_authority": self.design_authority,
            "derivation_ref": self.derivation_ref,
            "bindings": dict(self.bindings.refs),
            "state_version": self._state_version,
            "state": self._state,
            "governors": [asdict(spec) for spec in self._governors.values()],
            "generation": self._generation,
            "leases": [asdict(lease) for lease in self._leases.values()],
            "idempotency": {
                key: {
                    "fingerprint": fingerprint,
                    "receipt": asdict(receipt),
                    "owner": owner,
                }
                for key, (fingerprint, receipt, owner) in self._idempotency.items()
            },
            "invalidated_idempotency": sorted(self._invalidated_idempotency),
            "checkpoints": [asdict(checkpoint) for checkpoint in self._checkpoints.values()],
        }

    def _persist_if_enabled(self, reason: str) -> None:
        if not self._persistence_suspended:
            self._persist_snapshot(reason)

    def _persist_snapshot(self, reason: str) -> None:
        if self._persistence_suspended:
            return
        payload = self._snapshot()
        snapshot_hash = self._snapshot_hash(payload)
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT snapshot_hash, snapshot_json FROM iris_v1_snapshot_journal "
                "WHERE mission_id = ? ORDER BY seq DESC LIMIT 1",
                (self.mission_id,),
            ).fetchone()
            actual_head = str(row["snapshot_hash"]) if row else "GENESIS"
            if actual_head != self._durable_head_hash:
                connection.rollback()
                if row is not None:
                    latest_payload = json.loads(str(row["snapshot_json"]))
                    if self._snapshot_hash(latest_payload) != actual_head:
                        raise IrisV1InvariantError("IRIS_V1_DURABLE_SNAPSHOT_INTEGRITY_FAILURE")
                    self._persistence_suspended = True
                    try:
                        self._restore_snapshot(latest_payload)
                    finally:
                        self._persistence_suspended = False
                    self._durable_head_hash = actual_head
                raise IrisV1InvariantError("IRIS_V1_DURABLE_STALE_WRITER")
            connection.execute(
                "INSERT INTO iris_v1_snapshot_journal "
                "(mission_id, reason, state_version, predecessor_hash, snapshot_hash, snapshot_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.mission_id, reason, self._state_version, actual_head, snapshot_hash, serialized),
            )
            connection.commit()
            self._durable_head_hash = snapshot_hash
        finally:
            connection.close()

    def _load_latest_snapshot(self) -> tuple[dict[str, object], str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json, snapshot_hash FROM iris_v1_snapshot_journal "
                "WHERE mission_id = ? ORDER BY seq DESC LIMIT 1",
                (self.mission_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(str(row["snapshot_json"]))
        snapshot_hash = str(row["snapshot_hash"])
        if self._snapshot_hash(payload) != snapshot_hash:
            raise IrisV1InvariantError("IRIS_V1_DURABLE_SNAPSHOT_INTEGRITY_FAILURE")
        return payload, snapshot_hash

    def verify_snapshot_chain(self) -> bool:
        previous = "GENESIS"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT predecessor_hash, snapshot_hash, snapshot_json FROM iris_v1_snapshot_journal "
                "WHERE mission_id = ? ORDER BY seq ASC",
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

    def _restore_snapshot(self, payload: dict[str, object]) -> None:
        if payload.get("mission_id") != self.mission_id:
            raise IrisV1InvariantError("IRIS_V1_DURABLE_MISSION_MISMATCH")
        if payload.get("identity_state_root") != IRIS_IDENTITY_STATE_ROOT:
            raise IrisV1InvariantError("IRIS_V1_DURABLE_IDENTITY_ROOT_MISMATCH")
        if payload.get("design_authority") != IRIS_DESIGN_AUTHORITY:
            raise IrisV1InvariantError("IRIS_V1_DURABLE_DESIGN_AUTHORITY_MISMATCH")
        if payload.get("derivation_ref") != IRIS_DERIVATION_REF:
            raise IrisV1InvariantError("IRIS_V1_DURABLE_DERIVATION_REF_MISMATCH")
        IrisV1Bindings(payload.get("bindings", {})).assert_complete()

        raw_state = payload.get("state")
        if not isinstance(raw_state, dict) or set(raw_state) != set(NAMESPACE_OWNERS):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_NAMESPACE_SET_INVALID")

        canonical = {spec.governor_id: spec for spec in derived_governor_specs()}
        raw_governors = payload.get("governors")
        if not isinstance(raw_governors, list):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_GOVERNOR_ROSTER_INVALID")
        try:
            restored_governor_ids = [str(raw["governor_id"]) for raw in raw_governors]
        except (KeyError, TypeError):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_GOVERNOR_ROSTER_INVALID") from None
        if (
            len(restored_governor_ids) != len(canonical)
            or set(restored_governor_ids) != set(canonical)
        ):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_GOVERNOR_ROSTER_INCOMPLETE")

        owner_by_key: dict[str, str] = {}
        for spec in canonical.values():
            for key in spec.owned_state_keys:
                if key in owner_by_key:
                    raise IrisV1InvariantError("IRIS_V1_DURABLE_DUPLICATE_STATE_OWNER")
                owner_by_key[key] = spec.governor_id
        for key in raw_state.get(GOVERNOR_WRITABLE_NAMESPACE, {}):
            if key not in owner_by_key:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_STATE_KEY_OWNERSHIP_INVALID")

        self._state = {name: dict(values) for name, values in raw_state.items()}
        self._state_version = int(payload.get("state_version", 0))
        self._governors = {}
        for raw in raw_governors:
            spec = GovernorSpec(
                governor_id=str(raw["governor_id"]),
                role=str(raw["role"]),
                requirements=tuple(raw["requirements"]),
                writable_namespaces=tuple(raw["writable_namespaces"]),
                readable_namespaces=tuple(raw["readable_namespaces"]),
                owned_state_keys=tuple(raw["owned_state_keys"]),
                allowed_operations=tuple(raw["allowed_operations"]),
                authority_ceiling=str(raw["authority_ceiling"]),
            )
            self.register_governor(spec)

        raw_generation = payload.get("generation")
        if not isinstance(raw_generation, dict):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_GENERATION_OWNER_INVALID")
        self._generation = {str(key): int(value) for key, value in raw_generation.items()}
        if set(self._generation) != set(self._governors):
            raise IrisV1InvariantError("IRIS_V1_DURABLE_GENERATION_OWNER_SET_MISMATCH")

        self._leases = {}
        for raw in payload.get("leases", []):
            lease = GovernorLease(
                lease_id=str(raw["lease_id"]),
                mission_id=str(raw["mission_id"]),
                governor_id=str(raw["governor_id"]),
                scope=tuple(raw["scope"]),
                generation=int(raw["generation"]),
                valid_from=float(raw["valid_from"]),
                expires_at=float(raw["expires_at"]),
                authority_ref=str(raw["authority_ref"]),
                fenced=bool(raw["fenced"]),
            )
            spec = self._governors.get(lease.governor_id)
            if spec is None or lease.mission_id != self.mission_id or lease.authority_ref != spec.authority_ceiling:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_LEASE_INVALID")
            current_generation = self._generation.get(lease.governor_id)
            if current_generation is None:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_LEASE_OWNER_INVALID")
            if not lease.fenced and lease.generation != current_generation:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_ACTIVE_LEASE_GENERATION_INVALID")
            if lease.fenced and lease.generation > current_generation:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_FENCED_LEASE_GENERATION_INVALID")
            self._leases[lease.lease_id] = lease

        self._idempotency = {}
        for key, raw in payload.get("idempotency", {}).items():
            owner = str(raw["owner"])
            if owner not in self._governors:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_IDEMPOTENCY_OWNER_INVALID")
            receipt_raw = raw["receipt"]
            receipt = GovernanceReceipt(
                request_id=str(receipt_raw["request_id"]),
                status=DecisionStatus(str(receipt_raw["status"])),
                reason=str(receipt_raw["reason"]),
                mutation_count=int(receipt_raw["mutation_count"]),
                state_version_before=int(receipt_raw["state_version_before"]),
                state_version_after=int(receipt_raw["state_version_after"]),
                design_authority=str(receipt_raw["design_authority"]),
                identity_state_root=str(receipt_raw["identity_state_root"]),
                idempotent_replay=bool(receipt_raw.get("idempotent_replay", False)),
            )
            self._idempotency[str(key)] = (str(raw["fingerprint"]), receipt, owner)
        self._invalidated_idempotency = set(payload.get("invalidated_idempotency", []))

        self._checkpoints = {}
        for raw in payload.get("checkpoints", []):
            checkpoint = RecoveryCheckpoint(
                checkpoint_id=str(raw["checkpoint_id"]),
                mission_id=str(raw["mission_id"]),
                governor_id=str(raw["governor_id"]),
                generation=int(raw["generation"]),
                state_version=int(raw["state_version"]),
                owned_state=dict(raw["owned_state"]),
            )
            spec = self._governors.get(checkpoint.governor_id)
            if spec is None or checkpoint.mission_id != self.mission_id:
                raise IrisV1InvariantError("IRIS_V1_DURABLE_CHECKPOINT_OWNER_INVALID")
            if any(key not in spec.owned_state_keys for key in checkpoint.owned_state):
                raise IrisV1InvariantError("IRIS_V1_DURABLE_CHECKPOINT_STATE_OWNERSHIP_INVALID")
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
