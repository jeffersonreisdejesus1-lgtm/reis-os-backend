from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness


@dataclass(frozen=True)
class RealtimeBatch:
    events: tuple[CommandEvent, ...]
    next_cursor: int
    disconnected: bool
    freshness: Freshness


class CommandRealtimeFeed:
    """Projection-derived realtime feed for Command.

    This is transport only: it neither creates authority nor fabricates live state.
    Cursor positions are zero-based offsets into the durable B2 event order.
    """

    def __init__(self, store: CommandEventStore, *, max_batch: int = 100) -> None:
        if max_batch <= 0:
            raise ValueError("command_realtime_max_batch_invalid")
        self._store = store
        self._max_batch = max_batch

    def read(self, *, cursor: int = 0) -> RealtimeBatch:
        if cursor < 0:
            raise ValueError("command_realtime_cursor_invalid")
        events = self._store.read_all()
        if cursor > len(events):
            raise ValueError("command_realtime_cursor_ahead")
        selected = tuple(events[cursor : cursor + self._max_batch])
        return RealtimeBatch(
            events=selected,
            next_cursor=cursor + len(selected),
            disconnected=False,
            freshness=self._freshness(selected),
        )

    @staticmethod
    def _freshness(events: tuple[CommandEvent, ...]) -> Freshness:
        if not events:
            return Freshness.UNKNOWN
        values = {event.freshness for event in events}
        if Freshness.STALE in values:
            return Freshness.STALE
        if Freshness.UNKNOWN in values:
            return Freshness.UNKNOWN
        if values == {Freshness.LIVE}:
            return Freshness.LIVE
        return Freshness.RECENT


def encode_sse(batch: RealtimeBatch) -> Iterable[str]:
    for event in batch.events:
        payload = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "sequence": event.sequence,
            "source": event.source,
            "source_version": event.source_version,
            "freshness": event.freshness.value,
            "causation_id": event.causation_id,
            "correlation_id": event.correlation_id,
            "evidence_refs": list(event.evidence_refs),
            "payload": event.payload,
        }
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {data}\n\n"

    control = {
        "next_cursor": batch.next_cursor,
        "freshness": batch.freshness.value,
        "disconnected": batch.disconnected,
        "observed_at": datetime.now(UTC).isoformat(),
    }
    yield f"event: command.cursor\ndata: {json.dumps(control, sort_keys=True)}\n\n"
