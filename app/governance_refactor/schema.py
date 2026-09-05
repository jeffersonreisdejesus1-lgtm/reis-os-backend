from __future__ import annotations

import sqlite3
from pathlib import Path

from app.governance_refactor.projections import GovernanceProjectionError

RUNTIME_SCHEMA_VERSION = 2
_CORE_TABLES = frozenset(
    {"governance_candidate_records", "governance_candidate_events"}
)


def migrate_governance_candidate_store(database_path: str | Path) -> None:
    """Provision the dedicated SQLite store used by writer and projections.

    This is the sole physical schema authority for the external governance store.
    Alembic owns the application database and is not used for this file.
    """

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=30.0) as connection:
        connection.execute("BEGIN IMMEDIATE")
        names = _table_names(connection)
        if "governance_schema_meta" in names:
            row = connection.execute(
                "SELECT version FROM governance_schema_meta WHERE singleton=1"
            ).fetchone()
            if row is None:
                raise GovernanceProjectionError(
                    "governance_candidate_schema_meta_invalid"
                )
            if int(row[0]) > RUNTIME_SCHEMA_VERSION:
                raise GovernanceProjectionError("governance_candidate_schema_too_new")
        present_core = names.intersection(_CORE_TABLES)
        if present_core and present_core != _CORE_TABLES:
            raise GovernanceProjectionError("governance_candidate_schema_partial")
        if not present_core:
            _create_core(connection)
        _validate_core_columns(connection)
        _create_scope(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS governance_schema_meta (
                singleton INTEGER PRIMARY KEY CHECK (singleton=1),
                version INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO governance_schema_meta(singleton, version) VALUES(1, ?)
            ON CONFLICT(singleton) DO UPDATE SET version=excluded.version
            """,
            (RUNTIME_SCHEMA_VERSION,),
        )


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _create_core(connection: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE governance_candidate_records (
            position INTEGER PRIMARY KEY,
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            provenance_refs_json TEXT NOT NULL,
            written_at TEXT NOT NULL,
            UNIQUE(record_type, record_id, schema_version)
        )
        """,
        """
        CREATE INDEX ix_governance_candidate_records_type_id
        ON governance_candidate_records(record_type, record_id)
        """,
        """
        CREATE TABLE governance_candidate_events (
            position INTEGER PRIMARY KEY,
            event_id TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            provenance_refs_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        )
        """,
        """
        CREATE INDEX ix_governance_candidate_events_record
        ON governance_candidate_events(record_type, record_id, position)
        """,
    )
    for statement in statements:
        connection.execute(statement)


def _create_scope(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS governance_candidate_scopes (
            organization_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            bound_at TEXT NOT NULL,
            PRIMARY KEY (
                organization_id, record_type, record_id, schema_version
            ),
            UNIQUE(record_type, record_id, schema_version)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_governance_candidate_scopes_organization
        ON governance_candidate_scopes(organization_id, record_type)
        """
    )


def _validate_core_columns(connection: sqlite3.Connection) -> None:
    expected = {
        "governance_candidate_records": {
            "position", "record_type", "record_id", "schema_version",
            "payload_json", "payload_hash", "source_refs_json",
            "provenance_refs_json", "written_at",
        },
        "governance_candidate_events": {
            "position", "event_id", "record_type", "record_id",
            "schema_version", "event_type", "payload_hash", "payload_json",
            "source_refs_json", "provenance_refs_json", "occurred_at",
        },
    }
    for table, columns in expected.items():
        actual = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if actual != columns:
            raise GovernanceProjectionError("governance_candidate_schema_incompatible")
