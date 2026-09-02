from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .contracts import StateCommitRecord


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    trace_id: str
    seq: int
    event_type: str
    producer_kind: str
    ocs_id: str
    predecessors: tuple[str, ...]
    payload: dict[str, Any]
    previous_hash: str | None
    event_hash: str


class TraceCore:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, *, event_id: str, trace_id: str, event_type: str, producer_kind: str, ocs_id: str, predecessors: tuple[str, ...] = (), payload: dict[str, Any] | None = None) -> TraceEvent:
        previous_hash = self.events[-1].event_hash if self.events else None
        seq = len(self.events) + 1
        material = {"event_id": event_id, "trace_id": trace_id, "seq": seq, "event_type": event_type, "producer_kind": producer_kind, "ocs_id": ocs_id, "predecessors": predecessors, "payload": payload or {}, "previous_hash": previous_hash}
        event = TraceEvent(**material, event_hash=_hash(material))
        self.events.append(event)
        return event

    def verify(self) -> bool:
        previous_hash = None
        known: set[str] = set()
        for event in self.events:
            if event.previous_hash != previous_hash:
                return False
            if any(ref not in known for ref in event.predecessors):
                return False
            material = {"event_id": event.event_id, "trace_id": event.trace_id, "seq": event.seq, "event_type": event.event_type, "producer_kind": event.producer_kind, "ocs_id": event.ocs_id, "predecessors": event.predecessors, "payload": event.payload, "previous_hash": event.previous_hash}
            if _hash(material) != event.event_hash:
                return False
            known.add(event.event_id)
            previous_hash = event.event_hash
        return True

    def causal_status(self) -> str:
        return "PROVEN" if self.verify() else "NOT_PROVEN"


class StateCore:
    def __init__(self) -> None:
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._current: dict[str, int] = {}
        self._checkpoints: dict[str, tuple[str, int, str]] = {}

    def read_state(self, namespace: str) -> dict[str, Any] | None:
        version = self._current.get(namespace)
        if version is None:
            return None
        return dict(self._versions[namespace][version - 1]["state"])

    def commit_write(self, *, namespace: str, state: dict[str, Any], predecessor_version: int | None, authority_ref: str, action_id: str, trace_ref: str, committed_at: int) -> StateCommitRecord:
        current = self._current.get(namespace)
        if current != predecessor_version:
            raise ValueError("predecessor_mismatch")
        version = 1 if current is None else current + 1
        content_hash = _hash(state)
        row = {"version": version, "predecessor": predecessor_version, "state": dict(state), "hash": content_hash}
        self._versions.setdefault(namespace, []).append(row)
        readback = self._versions[namespace][-1]
        readback_hash = _hash(readback["state"])
        if readback_hash != content_hash:
            self._versions[namespace].pop()
            raise RuntimeError("readback_hash_mismatch")
        self._current[namespace] = version
        return StateCommitRecord(namespace, version, predecessor_version, content_hash, f"write:{namespace}:{version}", authority_ref, action_id, readback_hash, committed_at, None, trace_ref)

    def checkpoint(self, namespace: str, checkpoint_ref: str) -> None:
        version = self._current.get(namespace)
        if version is None:
            raise ValueError("no_state")
        row = self._versions[namespace][version - 1]
        self._checkpoints[checkpoint_ref] = (namespace, version, row["hash"])

    def rollback_to_verified(self, checkpoint_ref: str) -> dict[str, Any]:
        namespace, version, expected_hash = self._checkpoints[checkpoint_ref]
        row = self._versions[namespace][version - 1]
        if row["hash"] != expected_hash or _hash(row["state"]) != expected_hash:
            raise RuntimeError("checkpoint_not_verified")
        self._current[namespace] = version
        return dict(row["state"])

    def current_version(self, namespace: str) -> int | None:
        return self._current.get(namespace)
