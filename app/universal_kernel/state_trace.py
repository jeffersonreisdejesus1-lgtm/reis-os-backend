from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .contracts import StateRecord, TraceEvent, VerifiedCheckpoint


class StateCore:
    def __init__(self) -> None:
        self._records: dict[str, StateRecord] = {}
        self._current: dict[str, str] = {}

    def get(self, state_id: str) -> StateRecord:
        return self._records[state_id]

    def current(self, ocs: str) -> StateRecord | None:
        state_id = self._current.get(ocs)
        return self._records[state_id] if state_id is not None else None

    def write(
        self,
        record: StateRecord,
        readback_check: Callable[[StateRecord], bool],
    ) -> StateRecord:
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
        self._records[record.state_id] = record
        persisted = self._records[record.state_id]
        if not readback_check(persisted):
            self._records.pop(record.state_id, None)
            raise RuntimeError("state_readback_failed")
        self._current[record.ocs] = record.state_id
        return persisted

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
        return self.write(restored, lambda stored: stored == restored)


class TraceCore:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self.fail_next_append = False

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

    def chain_is_valid(self) -> bool:
        predecessor: str | None = None
        for event in self._events:
            if event.predecessor != predecessor:
                return False
            predecessor = event.event_id
        return True
