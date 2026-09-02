from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class TraceEvent:
    seq: int
    event_type: str
    payload: dict[str, str]
    previous_hash: str
    event_hash: str


class TraceLedger:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def append(self, event_type: str, payload: dict[str, str]) -> TraceEvent:
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        seq = len(self._events) + 1
        canonical = json.dumps(
            {
                "event_type": event_type,
                "payload": payload,
                "previous_hash": previous_hash,
                "seq": seq,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        event = TraceEvent(seq, event_type, dict(payload), previous_hash, digest)
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous_hash = "GENESIS"
        for event in self._events:
            canonical = json.dumps(
                {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "previous_hash": previous_hash,
                    "seq": event.seq,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            expected = sha256(canonical.encode("utf-8")).hexdigest()
            if event.previous_hash != previous_hash or event.event_hash != expected:
                return False
            previous_hash = event.event_hash
        return True

    def checkpoint_root(self) -> str:
        material = "|".join(event.event_hash for event in self._events)
        return sha256(material.encode("utf-8")).hexdigest()

    def mark_not_proven_if_broken(self) -> str:
        return "PROVEN" if self.verify() else "NOT_PROVEN"
