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

from app.governance_refactor.contracts import (
    SCHEMA_VERSION,
    CandidateRecord,
    record_id,
)
from app.governance_refactor.projections import (
    ALLOWED_RECORD_TYPES,
    GovernanceProjectionError,
)


class ScopedGovernanceStore:
    """Atomic organization-aware writer for the migrated 0004→0005 schema."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path)
        self._lock = RLock()
        health = self._health()
        if health != "available":
            raise GovernanceProjectionError(
                f"governance_candidate_schema_{health}"
            )

    def append(
        self,
        record: CandidateRecord,
        *,
        organization_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if not organization_id.strip():
            raise GovernanceProjectionError("candidate_organization_id_invalid")
        if occurred_at.tzinfo is None:
            raise GovernanceProjectionError("timezone_aware_timestamp_required")
        payload = _normalize(asdict(record))
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != SCHEMA_VERSION:
            raise GovernanceProjectionError("candidate_schema_version_incompatible")
        record_type = type(record).__name__
        if record_type not in ALLOWED_RECORD_TYPES:
            raise GovernanceProjectionError("candidate_record_type_not_allowed")
        identifier = record_id(record)
        payload_json = _canonical_json(payload)
        payload_hash = sha256(payload_json.encode()).hexdigest()
        source_refs = _refs(payload, "source_refs")
        provenance_refs = _refs(payload, "provenance_refs")
        timestamp = occurred_at.isoformat()
        event_id = sha256(
            f"{record_type}:{identifier}:{schema_version}:{payload_hash}".encode()
        ).hexdigest()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT r.*, s.organization_id AS scoped_organization_id
                FROM governance_candidate_records r
                LEFT JOIN governance_candidate_scopes s
                  ON s.record_type=r.record_type
                 AND s.record_id=r.record_id
                 AND s.schema_version=r.schema_version
                WHERE r.record_type=? AND r.record_id=? AND r.schema_version=?
                """,
                (record_type, identifier, schema_version),
            ).fetchone()
            if existing is not None:
                return self._replay(
                    existing,
                    organization_id=organization_id,
                    payload_hash=payload_hash,
                    source_refs=source_refs,
                    provenance_refs=provenance_refs,
                )
            record_position = _next_position(
                connection, "governance_candidate_records"
            )
            event_position = _next_position(
                connection, "governance_candidate_events"
            )
            connection.execute(
                """
                INSERT INTO governance_candidate_records (
                    position, record_type, record_id, schema_version, payload_json,
                    payload_hash, source_refs_json, provenance_refs_json, written_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_position,
                    record_type,
                    identifier,
                    schema_version,
                    payload_json,
                    payload_hash,
                    _canonical_json(source_refs),
                    _canonical_json(provenance_refs),
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO governance_candidate_events (
                    position, event_id, record_type, record_id, schema_version,
                    event_type, payload_hash, payload_json, source_refs_json,
                    provenance_refs_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_position,
                    event_id,
                    record_type,
                    identifier,
                    schema_version,
                    "CANDIDATE_RECORD_APPENDED",
                    payload_hash,
                    payload_json,
                    _canonical_json(source_refs),
                    _canonical_json(provenance_refs),
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO governance_candidate_scopes (
                    organization_id, record_type, record_id, schema_version, bound_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    record_type,
                    identifier,
                    schema_version,
                    timestamp,
                ),
            )
        return {
            "record_type": record_type,
            "record_id": identifier,
            "payload_hash": payload_hash,
            "organization_id": organization_id,
            "replayed": False,
        }

    def _replay(
        self,
        row: sqlite3.Row,
        *,
        organization_id: str,
        payload_hash: str,
        source_refs: list[str],
        provenance_refs: list[str],
    ) -> dict[str, Any]:
        owner = row["scoped_organization_id"]
        if owner is None:
            raise GovernanceProjectionError("candidate_unscoped_record_conflict")
        if str(owner) != organization_id:
            raise GovernanceProjectionError("candidate_scope_conflict")
        if str(row["payload_hash"]) != payload_hash:
            raise GovernanceProjectionError("candidate_append_conflict")
        if json.loads(str(row["source_refs_json"])) != source_refs:
            raise GovernanceProjectionError("candidate_evidence_envelope_mismatch")
        if json.loads(str(row["provenance_refs_json"])) != provenance_refs:
            raise GovernanceProjectionError("candidate_evidence_envelope_mismatch")
        return {
            "record_type": str(row["record_type"]),
            "record_id": str(row["record_id"]),
            "payload_hash": payload_hash,
            "organization_id": organization_id,
            "replayed": True,
        }

    def _health(self) -> str:
        if not self._path.is_file():
            return "unavailable"
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
        except sqlite3.Error:
            return "error"
        names = {str(row["name"]) for row in rows}
        required = {
            "governance_candidate_records",
            "governance_candidate_events",
            "governance_candidate_scopes",
        }
        return "available" if required.issubset(names) else "incompatible"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection


def _next_position(connection: sqlite3.Connection, table: str) -> int:
    if table not in {"governance_candidate_records", "governance_candidate_events"}:
        raise GovernanceProjectionError("candidate_position_table_invalid")
    sql = f"SELECT COALESCE(MAX(position), 0) + 1 FROM {table}"
    row = connection.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def _refs(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    return [str(item) for item in value] if isinstance(value, list) else []


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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
