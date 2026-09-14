from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .contracts import MissionSnapshot, MissionStatus, RepositoryEffectReceipt


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
                    transcript_ref TEXT
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
                """
                INSERT INTO missions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.mission_id,
                    snapshot.organization_id,
                    snapshot.ocs_id,
                    snapshot.authority_ref,
                    snapshot.state_namespace,
                    snapshot.memory_namespace,
                    snapshot.generation,
                    snapshot.instance_id,
                    snapshot.status.value,
                    snapshot.checkpoint_version,
                    snapshot.checkpoint_hash,
                    snapshot.transcript_ref,
                ),
            )
            self._append_event(
                connection,
                snapshot.mission_id,
                "MISSION_CREATED",
                {
                    "generation": snapshot.generation,
                    "instance_id": snapshot.instance_id,
                },
            )

    def save(self, snapshot: MissionSnapshot, event_type: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE missions
                SET generation=?, instance_id=?, status=?, checkpoint_version=?,
                    checkpoint_hash=?, transcript_ref=?
                WHERE mission_id=? AND organization_id=? AND ocs_id=?
                    AND authority_ref=?
                """,
                (
                    snapshot.generation,
                    snapshot.instance_id,
                    snapshot.status.value,
                    snapshot.checkpoint_version,
                    snapshot.checkpoint_hash,
                    snapshot.transcript_ref,
                    snapshot.mission_id,
                    snapshot.organization_id,
                    snapshot.ocs_id,
                    snapshot.authority_ref,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("mission_identity_or_authority_mismatch")
            self._append_event(
                connection,
                snapshot.mission_id,
                event_type,
                {
                    "generation": snapshot.generation,
                    "instance_id": snapshot.instance_id,
                    "status": snapshot.status.value,
                    "checkpoint_version": snapshot.checkpoint_version,
                },
            )

    def load(self, mission_id: str) -> MissionSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise KeyError(mission_id)
        return MissionSnapshot(
            mission_id=row["mission_id"],
            organization_id=row["organization_id"],
            ocs_id=row["ocs_id"],
            authority_ref=row["authority_ref"],
            state_namespace=row["state_namespace"],
            memory_namespace=row["memory_namespace"],
            generation=row["generation"],
            instance_id=row["instance_id"],
            status=MissionStatus(row["status"]),
            checkpoint_version=row["checkpoint_version"],
            checkpoint_hash=row["checkpoint_hash"],
            transcript_ref=row["transcript_ref"],
        )

    def effect(
        self,
        mission_id: str,
        idempotency_key: str,
    ) -> RepositoryEffectReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM effects WHERE mission_id=? AND idempotency_key=?",
                (mission_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return RepositoryEffectReceipt(
            mission_id=row["mission_id"],
            idempotency_key=row["idempotency_key"],
            generation=row["generation"],
            path=row["path"],
            before_hash=row["before_hash"],
            after_hash=row["after_hash"],
            duplicate_effect=False,
            readback_hash=row["readback_hash"],
        )

    def record_effect(
        self,
        receipt: RepositoryEffectReceipt,
        payload: dict[str, str],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO effects VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.mission_id,
                    receipt.idempotency_key,
                    receipt.generation,
                    receipt.path,
                    receipt.before_hash,
                    receipt.after_hash,
                    receipt.readback_hash,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            self._append_event(
                connection,
                receipt.mission_id,
                "MATERIAL_EFFECT_APPLIED",
                {"idempotency_key": receipt.idempotency_key, "path": receipt.path},
            )

    def event_types(self, mission_id: str) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_type FROM events WHERE mission_id=? ORDER BY sequence",
                (mission_id,),
            ).fetchall()
        return tuple(str(row["event_type"]) for row in rows)

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        mission_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        connection.execute(
            "INSERT INTO events(mission_id, event_type, payload_json) VALUES (?, ?, ?)",
            (mission_id, event_type, json.dumps(payload, sort_keys=True)),
        )
