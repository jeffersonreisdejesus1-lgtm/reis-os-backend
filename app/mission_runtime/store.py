from __future__ import annotations

# ruff: noqa: E501

import json
import sqlite3
from pathlib import Path

from .contracts import (
    BindingStatus,
    MissionSnapshot,
    MissionStatus,
    RepositoryEffectReceipt,
)


class MissionRuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    ocs_id TEXT NOT NULL,
                    authority_ref TEXT NOT NULL,
                    state_namespace TEXT NOT NULL,
                    memory_namespace TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checkpoint_version INTEGER NOT NULL,
                    checkpoint_hash TEXT,
                    transcript_ref TEXT,
                    binding_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                    binding_evidence TEXT,
                    checkpoint_material_json TEXT
                );
                CREATE TABLE IF NOT EXISTS effects (
                    mission_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    before_hash TEXT NOT NULL,
                    after_hash TEXT NOT NULL,
                    readback_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'APPLIED',
                    requested_hash TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (mission_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def create(self, snapshot: MissionSnapshot) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO missions(
                    mission_id, organization_id, ocs_id, authority_ref,
                    state_namespace, memory_namespace, generation, instance_id,
                    status, checkpoint_version, checkpoint_hash, transcript_ref,
                    binding_status, binding_evidence, checkpoint_material_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.mission_id, snapshot.organization_id, snapshot.ocs_id,
                    snapshot.authority_ref, snapshot.state_namespace, snapshot.memory_namespace,
                    snapshot.generation, snapshot.instance_id, snapshot.status.value,
                    snapshot.checkpoint_version, snapshot.checkpoint_hash,
                    snapshot.transcript_ref, snapshot.binding_status.value,
                    snapshot.binding_evidence, snapshot.checkpoint_material_json,
                ),
            )
            self._append_event(connection, snapshot.mission_id, "MISSION_CREATED", {
                "generation": snapshot.generation, "instance_id": snapshot.instance_id
            })

    def save(self, snapshot: MissionSnapshot, event_type: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE missions SET generation=?, instance_id=?, status=?,
                    checkpoint_version=?, checkpoint_hash=?, transcript_ref=?,
                    binding_status=?, binding_evidence=?, checkpoint_material_json=?
                    WHERE mission_id=? AND organization_id=? AND ocs_id=? AND authority_ref=?""",
                (
                    snapshot.generation, snapshot.instance_id, snapshot.status.value,
                    snapshot.checkpoint_version, snapshot.checkpoint_hash,
                    snapshot.transcript_ref, snapshot.binding_status.value,
                    snapshot.binding_evidence, snapshot.checkpoint_material_json,
                    snapshot.mission_id, snapshot.organization_id, snapshot.ocs_id,
                    snapshot.authority_ref,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("mission_identity_or_authority_mismatch")
            self._append_event(connection, snapshot.mission_id, event_type, {
                "generation": snapshot.generation, "instance_id": snapshot.instance_id,
                "status": snapshot.status.value, "checkpoint_version": snapshot.checkpoint_version
            })

    def load(self, mission_id: str) -> MissionSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise KeyError(mission_id)
        return MissionSnapshot(
            mission_id=row["mission_id"], organization_id=row["organization_id"],
            ocs_id=row["ocs_id"], authority_ref=row["authority_ref"],
            state_namespace=row["state_namespace"], memory_namespace=row["memory_namespace"],
            generation=row["generation"], instance_id=row["instance_id"],
            status=MissionStatus(row["status"]),
            checkpoint_version=row["checkpoint_version"],
            checkpoint_hash=row["checkpoint_hash"], transcript_ref=row["transcript_ref"],
            binding_status=BindingStatus(row["binding_status"]),
            binding_evidence=row["binding_evidence"],
            checkpoint_material_json=row["checkpoint_material_json"],
        )

    def claim_effect(self, mission_id: str, idempotency_key: str, *, generation: int,
                     path: str, requested_hash: str) -> tuple[str, str, str] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, path, requested_hash FROM effects "
                "WHERE mission_id=? AND idempotency_key=?", (mission_id, idempotency_key)
            ).fetchone()
            if row is not None:
                connection.commit()
                return str(row["status"]), str(row["path"]), str(row["requested_hash"])
            connection.execute(
                """INSERT INTO effects(
                    mission_id, idempotency_key, generation, path,
                    before_hash, after_hash, readback_hash, payload_json, status, requested_hash
                ) VALUES (?, ?, ?, ?, '', '', '', ?, 'PENDING', ?)""",
                (mission_id, idempotency_key, generation, path,
                 json.dumps({"content_hash": requested_hash}, sort_keys=True), requested_hash),
            )
            connection.commit()
            return None

    def effect(self, mission_id: str, idempotency_key: str) -> RepositoryEffectReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM effects WHERE mission_id=? AND idempotency_key=? AND status='APPLIED'",
                (mission_id, idempotency_key)
            ).fetchone()
        if row is None:
            return None
        return RepositoryEffectReceipt(
            mission_id=row["mission_id"], idempotency_key=row["idempotency_key"],
            generation=row["generation"], path=row["path"],
            before_hash=row["before_hash"], after_hash=row["after_hash"],
            duplicate_effect=False, readback_hash=row["readback_hash"],
        )

    def apply_effect(self, receipt: RepositoryEffectReceipt, payload: dict[str, str]) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE effects SET before_hash=?, after_hash=?, readback_hash=?,
                    payload_json=?, status='APPLIED'
                    WHERE mission_id=? AND idempotency_key=? AND status='PENDING'""",
                (receipt.before_hash, receipt.after_hash, receipt.readback_hash,
                 json.dumps(payload, sort_keys=True), receipt.mission_id, receipt.idempotency_key),
            )
            if cursor.rowcount != 1:
                raise ValueError("mission_effect_claim_not_pending")
            self._append_event(connection, receipt.mission_id, "MATERIAL_EFFECT_APPLIED", {
                "idempotency_key": receipt.idempotency_key, "path": receipt.path,
                "after_hash": receipt.after_hash,
            })

    def effect_records(self, mission_id: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT idempotency_key, generation, path, before_hash, after_hash, "
                "readback_hash, requested_hash FROM effects "
                "WHERE mission_id=? AND status='APPLIED' ORDER BY idempotency_key",
                (mission_id,),
            ).fetchall()
        return [{
            "idempotency_key": str(row["idempotency_key"]),
            "generation": str(row["generation"]),
            "path": str(row["path"]), "before_hash": str(row["before_hash"]),
            "after_hash": str(row["after_hash"]), "readback_hash": str(row["readback_hash"]),
            "requested_hash": str(row["requested_hash"]),
        } for row in rows]

    def checkpoint_effects_match(self, mission_id: str, records: list[dict[str, str]]) -> bool:
        current = {r["idempotency_key"]: r for r in self.effect_records(mission_id)}
        return all(current.get(r["idempotency_key"]) == r for r in records)

    @staticmethod
    def _append_event(connection: sqlite3.Connection, mission_id: str,
                      event_type: str, payload: dict[str, object]) -> None:
        connection.execute(
            "INSERT INTO events(mission_id, event_type, payload_json) VALUES (?, ?, ?)",
            (mission_id, event_type, json.dumps(payload, sort_keys=True)),
        )
