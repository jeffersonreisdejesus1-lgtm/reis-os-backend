from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.command.events import CommandEvent, EventValidationError, Freshness


class EventStoreError(RuntimeError):
    pass


class CommandEventStore:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_events (
                    position INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    institution_id TEXT NOT NULL,
                    ocs_id TEXT,
                    project_id TEXT,
                    run_id TEXT,
                    causation_id TEXT,
                    correlation_id TEXT,
                    sequence INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    freshness TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(source, institution_id, ocs_id, run_id, sequence)
                )
                """
            )

    def append(self, event: CommandEvent) -> bool:
        event.validate()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT event_id FROM command_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["event_id"] != event.event_id:
                    raise EventStoreError("command_event_idempotency_conflict")
                return False

            previous = connection.execute(
                """
                SELECT MAX(sequence) AS last_sequence
                FROM command_events
                WHERE source = ? AND institution_id = ?
                  AND ocs_id IS ? AND run_id IS ?
                """,
                (event.source, event.institution_id, event.ocs_id, event.run_id),
            ).fetchone()
            last_sequence = previous["last_sequence"] if previous else None
            expected = 1 if last_sequence is None else int(last_sequence) + 1
            if event.sequence != expected:
                raise EventValidationError("command_event_sequence_hold")

            try:
                connection.execute(
                    """
                    INSERT INTO command_events (
                        event_id, event_type, schema_version, occurred_at,
                        source, source_version, institution_id, ocs_id,
                        project_id, run_id, causation_id, correlation_id,
                        sequence, idempotency_key, freshness,
                        evidence_refs, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.event_type,
                        event.schema_version,
                        event.occurred_at_utc(),
                        event.source,
                        event.source_version,
                        event.institution_id,
                        event.ocs_id,
                        event.project_id,
                        event.run_id,
                        event.causation_id,
                        event.correlation_id,
                        event.sequence,
                        event.idempotency_key,
                        event.freshness.value,
                        json.dumps(event.evidence_refs, sort_keys=True),
                        json.dumps(
                            event.payload,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise EventStoreError("command_event_integrity_rejected") from exc
        return True

    def read_all(self) -> list[CommandEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM command_events ORDER BY position ASC"
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def replay(self) -> Iterable[CommandEvent]:
        return tuple(self.read_all())

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> CommandEvent:
        from datetime import datetime

        payload: dict[str, Any] = json.loads(row["payload"])
        refs = tuple(str(item) for item in json.loads(row["evidence_refs"]))
        return CommandEvent(
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            schema_version=str(row["schema_version"]),
            occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
            source=str(row["source"]),
            source_version=str(row["source_version"]),
            institution_id=str(row["institution_id"]),
            ocs_id=row["ocs_id"],
            project_id=row["project_id"],
            run_id=row["run_id"],
            causation_id=row["causation_id"],
            correlation_id=row["correlation_id"],
            sequence=int(row["sequence"]),
            idempotency_key=str(row["idempotency_key"]),
            freshness=Freshness(str(row["freshness"])),
            evidence_refs=refs,
            payload=payload,
        )
