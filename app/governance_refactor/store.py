from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any

from app.governance_refactor.contracts import SCHEMA_VERSION, CandidateRecord, record_id

_REQUIRED_SCHEMA: dict[str, frozenset[str]] = {
    "governance_candidate_records": frozenset(
        {
            "position",
            "record_type",
            "record_id",
            "schema_version",
            "payload_json",
            "payload_hash",
            "source_refs_json",
            "provenance_refs_json",
            "written_at",
        }
    ),
    "governance_candidate_events": frozenset(
        {
            "position",
            "event_id",
            "record_type",
            "record_id",
            "schema_version",
            "event_type",
            "payload_hash",
            "payload_json",
            "source_refs_json",
            "provenance_refs_json",
            "occurred_at",
        }
    ),
}


class GovernancePersistenceError(RuntimeError):
    pass


class GovernanceCandidateStore:
    """Append-only access to already-migrated governance candidate tables.

    Alembic is the sole physical schema authority. This application store validates
    revision-0004-compatible tables and fails closed when they are absent or
    incompatible. It never creates, alters or repairs production schema and has no
    authority, lifecycle, Kernel, Hazel or Binder side effects.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._lock = RLock()
        self._validate_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _validate_schema(self) -> None:
        with self._connect() as connection:
            for table, expected_columns in _REQUIRED_SCHEMA.items():
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (table,),
                ).fetchone()
                if exists is None:
                    raise GovernancePersistenceError(
                        "governance_candidate_migration_0004_required"
                    )
                actual_columns = {
                    str(row["name"])
                    for row in connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                }
                if actual_columns != expected_columns:
                    raise GovernancePersistenceError(
                        "governance_candidate_schema_incompatible"
                    )

    def append(
        self,
        record: CandidateRecord,
        *,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if occurred_at.tzinfo is None:
            raise GovernancePersistenceError("timezone_aware_timestamp_required")
        payload = _normalize(asdict(record))
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != SCHEMA_VERSION:
            raise GovernancePersistenceError("candidate_schema_version_incompatible")
        record_type = type(record).__name__
        identifier = record_id(record)
        payload_json = _canonical_json(payload)
        payload_hash = sha256(payload_json.encode()).hexdigest()
        source_refs = _extract_refs(payload, "source_refs")
        provenance_refs = _extract_refs(payload, "provenance_refs")
        written_at = occurred_at.isoformat()
        event_id = sha256(
            f"{record_type}:{identifier}:{schema_version}:{payload_hash}".encode()
        ).hexdigest()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM governance_candidate_records
                WHERE record_type = ? AND record_id = ? AND schema_version = ?
                """,
                (record_type, identifier, schema_version),
            ).fetchone()
            if existing is not None:
                if str(existing["payload_hash"]) != payload_hash:
                    raise GovernancePersistenceError("candidate_append_conflict")
                return _record_from_row(existing)
            connection.execute(
                """
                INSERT INTO governance_candidate_records (
                    record_type, record_id, schema_version, payload_json,
                    payload_hash, source_refs_json, provenance_refs_json, written_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_type,
                    identifier,
                    schema_version,
                    payload_json,
                    payload_hash,
                    _canonical_json(source_refs),
                    _canonical_json(provenance_refs),
                    written_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO governance_candidate_events (
                    event_id, record_type, record_id, schema_version, event_type,
                    payload_hash, payload_json, source_refs_json,
                    provenance_refs_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    record_type,
                    identifier,
                    schema_version,
                    "CANDIDATE_RECORD_APPENDED",
                    payload_hash,
                    payload_json,
                    _canonical_json(source_refs),
                    _canonical_json(provenance_refs),
                    written_at,
                ),
            )
        return self.read(record_type, identifier, schema_version=schema_version)

    def read(
        self,
        record_type: str,
        identifier: str,
        *,
        schema_version: str = SCHEMA_VERSION,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM governance_candidate_records
                WHERE record_type = ? AND record_id = ? AND schema_version = ?
                """,
                (record_type, identifier, schema_version),
            ).fetchone()
        if row is None:
            raise GovernancePersistenceError("candidate_record_not_found")
        return _record_from_row(row)

    def replay(self, *, after_position: int = 0) -> tuple[dict[str, Any], ...]:
        if after_position < 0:
            raise GovernancePersistenceError("negative_replay_position")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM governance_candidate_events
                WHERE position > ? ORDER BY position ASC
                """,
                (after_position,),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            payload_json = str(row["payload_json"])
            if sha256(payload_json.encode()).hexdigest() != str(row["payload_hash"]):
                raise GovernancePersistenceError("candidate_replay_hash_mismatch")
            events.append(
                {
                    "position": int(row["position"]),
                    "event_id": str(row["event_id"]),
                    "record_type": str(row["record_type"]),
                    "record_id": str(row["record_id"]),
                    "schema_version": str(row["schema_version"]),
                    "event_type": str(row["event_type"]),
                    "payload_hash": str(row["payload_hash"]),
                    "payload": json.loads(payload_json),
                    "source_refs": json.loads(str(row["source_refs_json"])),
                    "provenance_refs": json.loads(str(row["provenance_refs_json"])),
                    "occurred_at": str(row["occurred_at"]),
                }
            )
        return tuple(events)

    def event_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM governance_candidate_events"
            ).fetchone()
        return 0 if row is None else int(row["count"])


def _record_from_row(row: sqlite3.Row) -> dict[str, Any]:
    payload_json = str(row["payload_json"])
    if sha256(payload_json.encode()).hexdigest() != str(row["payload_hash"]):
        raise GovernancePersistenceError("candidate_readback_hash_mismatch")
    return {
        "record_type": str(row["record_type"]),
        "record_id": str(row["record_id"]),
        "schema_version": str(row["schema_version"]),
        "payload": json.loads(payload_json),
        "payload_hash": str(row["payload_hash"]),
        "source_refs": json.loads(str(row["source_refs_json"])),
        "provenance_refs": json.loads(str(row["provenance_refs_json"])),
        "written_at": str(row["written_at"]),
    }


def _extract_refs(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _normalize(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalize(item) for item in value]
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
