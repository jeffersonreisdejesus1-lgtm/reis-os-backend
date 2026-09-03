from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace
from hashlib import sha256
from json import JSONDecodeError, dumps, loads
from pathlib import Path
from sqlite3 import Connection, connect
from typing import Protocol

from .contracts import StateRecord, TraceEvent, VerifiedCheckpoint


def _canonical_state_json(record: StateRecord) -> str:
    try:
        return dumps(
            asdict(record),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("state_payload_not_serializable") from exc


def state_record_hash(record: StateRecord) -> str:
    return sha256(_canonical_state_json(record).encode("utf-8")).hexdigest()


def _state_from_json(raw: str) -> StateRecord:
    try:
        data = loads(raw)
    except JSONDecodeError as exc:
        raise RuntimeError("state_durable_integrity_failed") from exc
    if not isinstance(data, dict):
        raise RuntimeError("state_durable_integrity_failed")
    try:
        payload = data["payload"]
        if not isinstance(payload, dict):
            raise TypeError
        return StateRecord(
            state_id=str(data["state_id"]),
            ocs=str(data["ocs"]),
            version=int(data["version"]),
            predecessor=(
                None if data["predecessor"] is None else str(data["predecessor"])
            ),
            payload=payload,
            verified=bool(data["verified"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("state_durable_integrity_failed") from exc


class StatePersistencePort(Protocol):
    @property
    def durable(self) -> bool: ...

    def write(self, record: StateRecord) -> None: ...

    def read_fresh(self, state_id: str) -> StateRecord: ...

    def load_all(self) -> tuple[StateRecord, ...]: ...

    def delete(self, state_id: str) -> None: ...


class SQLiteStatePersistencePort:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def durable(self) -> bool:
        return True

    def _connection(self) -> Connection:
        return connect(self._database_path)

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS state_records (
                    state_id TEXT PRIMARY KEY,
                    ocs TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    predecessor TEXT,
                    record_json TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    UNIQUE (ocs, version)
                )
                """
            )

    def write(self, record: StateRecord) -> None:
        raw = _canonical_state_json(record)
        digest = state_record_hash(record)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO state_records (
                    state_id, ocs, version, predecessor, record_json, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.state_id,
                    record.ocs,
                    record.version,
                    record.predecessor,
                    raw,
                    digest,
                ),
            )

    def read_fresh(self, state_id: str) -> StateRecord:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT record_json, record_hash
                FROM state_records
                WHERE state_id = ?
                """,
                (state_id,),
            ).fetchone()
        if row is None:
            raise KeyError(state_id)
        raw, stored_hash = str(row[0]), str(row[1])
        record = _state_from_json(raw)
        if state_record_hash(record) != stored_hash:
            raise RuntimeError("state_durable_integrity_failed")
        return record

    def load_all(self) -> tuple[StateRecord, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT state_id
                FROM state_records
                ORDER BY ocs ASC, version ASC
                """
            ).fetchall()
        return tuple(self.read_fresh(str(row[0])) for row in rows)

    def delete(self, state_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM state_records WHERE state_id = ?",
                (state_id,),
            )

    def corrupt_payload_for_test(
        self,
        state_id: str,
        payload: dict[str, object],
    ) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT record_json FROM state_records WHERE state_id = ?",
                (state_id,),
            ).fetchone()
            if row is None:
                raise KeyError(state_id)
            data = loads(str(row[0]))
            data["payload"] = payload
            connection.execute(
                "UPDATE state_records SET record_json = ? WHERE state_id = ?",
                (
                    dumps(
                        data,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                    state_id,
                ),
            )


class StateCore:
    def __init__(self, persistence: StatePersistencePort | None = None) -> None:
        self._records: dict[str, StateRecord] = {}
        self._current: dict[str, str] = {}
        self._persistence = persistence
        if persistence is not None:
            if not persistence.durable:
                raise ValueError("state_persistence_port_must_be_durable")
            self._reload_from_durable_state()

    @property
    def durable_persistence_enabled(self) -> bool:
        return self._persistence is not None and self._persistence.durable

    def _reload_from_durable_state(self) -> None:
        assert self._persistence is not None
        records = self._persistence.load_all()
        for record in records:
            if record.state_id in self._records:
                raise RuntimeError("state_durable_integrity_failed")
            current_id = self._current.get(record.ocs)
            if current_id is None:
                if record.version != 1 or record.predecessor is not None:
                    raise RuntimeError("state_durable_integrity_failed")
            else:
                current = self._records[current_id]
                if record.version != current.version + 1:
                    raise RuntimeError("state_durable_integrity_failed")
                if record.predecessor != current.state_id:
                    raise RuntimeError("state_durable_integrity_failed")
            self._records[record.state_id] = record
            self._current[record.ocs] = record.state_id

    def get(self, state_id: str) -> StateRecord:
        return self._records[state_id]

    def current(self, ocs: str) -> StateRecord | None:
        state_id = self._current.get(ocs)
        return self._records[state_id] if state_id is not None else None

    def write(
        self,
        record: StateRecord,
        readback_check: Callable[[StateRecord], bool],
        *,
        actor_ocs_id: str | None = None,
        target_namespace: str | None = None,
        state_ref: str | None = None,
        authority_context: str | None = None,
    ) -> StateRecord:
        if actor_ocs_id is None:
            raise ValueError("state_actor_ocs_required")
        if target_namespace is None:
            raise ValueError("state_namespace_required")
        if state_ref is None:
            raise ValueError("state_ref_required")
        if authority_context is None or not authority_context:
            raise ValueError("state_authority_context_required")
        self._validate_namespace(actor_ocs_id, target_namespace, record.ocs)
        if state_ref != record.state_id:
            raise ValueError("state_ref_mismatch")
        if record.version < 1:
            raise ValueError("state_version_required")
        current = self.current(record.ocs)
        if current is None:
            if record.predecessor is not None:
                raise ValueError("genesis_predecessor_must_be_none")
            if record.version != 1:
                raise ValueError("genesis_version_must_be_one")
        else:
            if record.predecessor != current.state_id:
                raise ValueError("predecessor_required")
            if record.version != current.version + 1:
                raise ValueError("state_version_must_increment")

        if self._persistence is not None:
            self._persistence.write(record)
            try:
                persisted = self._persistence.read_fresh(record.state_id)
                if (
                    persisted.state_id != record.state_id
                    or persisted.ocs != record.ocs
                    or persisted.version != record.version
                    or persisted.predecessor != record.predecessor
                    or state_record_hash(persisted) != state_record_hash(record)
                    or not readback_check(persisted)
                ):
                    raise RuntimeError("state_readback_failed")
            except Exception:
                self._persistence.delete(record.state_id)
                raise
        else:
            self._records[record.state_id] = record
            persisted = self._records[record.state_id]
            if not readback_check(persisted):
                self._records.pop(record.state_id, None)
                raise RuntimeError("state_readback_failed")

        self._records[record.state_id] = persisted
        self._current[record.ocs] = record.state_id
        return persisted

    @staticmethod
    def _validate_namespace(
        actor_ocs_id: str,
        target_namespace: str,
        record_ocs: str,
    ) -> None:
        prefix = "state://"
        if not target_namespace.startswith(prefix):
            raise ValueError("state_namespace_invalid")
        owner = target_namespace[len(prefix) :].split("/", 1)[0]
        if not owner:
            raise ValueError("state_namespace_owner_required")
        if owner.casefold() != record_ocs.casefold():
            raise ValueError("state_namespace_record_owner_mismatch")
        if actor_ocs_id.casefold() != owner.casefold():
            raise ValueError("state_namespace_violation")

    def restore_verified(self, checkpoint: VerifiedCheckpoint) -> StateRecord:
        if not checkpoint.state.verified:
            raise ValueError("verified_checkpoint_required")
        current = self.current(checkpoint.state.ocs)
        restored_version = 1 if current is None else current.version + 1
        restored = replace(
            checkpoint.state,
            state_id=f"recovery:{checkpoint.checkpoint_id}:{restored_version}",
            version=restored_version,
            predecessor=current.state_id if current is not None else None,
            verified=True,
        )
        return self.write(
            restored,
            lambda stored: stored == restored,
            actor_ocs_id=restored.ocs,
            target_namespace=f"state://{restored.ocs}/recovery",
            state_ref=restored.state_id,
            authority_context="recovery:verified-checkpoint",
        )


class TraceCore:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self.fail_next_append = False
        self.fail_next_preflight = False
        self.fail_next_finalization = False

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def append(self, event: TraceEvent) -> None:
        if self.fail_next_append:
            self.fail_next_append = False
            raise RuntimeError("trace_append_failed")
        expected_predecessor = self._events[-1].event_id if self._events else None
        if event.predecessor != expected_predecessor:
            raise ValueError("trace_predecessor_mismatch")
        self._events.append(event)

    def append_stage(
        self,
        *,
        event_id: str,
        action_id: str,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> TraceEvent:
        if stage == "TRACE_CLOSE" and self.fail_next_finalization:
            self.fail_next_finalization = False
            raise RuntimeError("trace_finalization_failed")
        predecessor = self._events[-1].event_id if self._events else None
        event = TraceEvent(
            event_id=event_id,
            action_id=action_id,
            stage=stage,
            predecessor=predecessor,
            details={} if details is None else details,
        )
        self.append(event)
        return event

    def preflight_gate(self) -> None:
        if self.fail_next_preflight:
            self.fail_next_preflight = False
            raise RuntimeError("trace_preflight_failed")

    def preflight(
        self,
        *,
        event_id: str,
        action_id: str,
        trace_id: str,
        authority_ref: str,
        lease_id: str,
    ) -> TraceEvent:
        self.preflight_gate()
        return self.append_stage(
            event_id=event_id,
            action_id=action_id,
            stage="TRACE_PREFLIGHT",
            details={
                "trace_id": trace_id,
                "authority_ref": authority_ref,
                "lease_id": lease_id,
            },
        )

    def chain_is_valid(self) -> bool:
        predecessor: str | None = None
        for event in self._events:
            if event.predecessor != predecessor:
                return False
            predecessor = event.event_id
        return True
