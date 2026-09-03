from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

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
        self._records[record.state_id] = record
        persisted = self._records[record.state_id]
        if not readback_check(persisted):
            self._records.pop(record.state_id, None)
            raise RuntimeError("state_readback_failed")
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
