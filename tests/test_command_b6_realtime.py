from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness
from app.command.realtime import CommandRealtimeFeed, encode_sse


def _event(sequence: int, freshness: Freshness = Freshness.LIVE) -> CommandEvent:
    return CommandEvent(
        event_id=f"evt-{sequence}",
        event_type="operation.updated",
        schema_version="1",
        occurred_at=datetime(2026, 9, 5, 6, sequence, tzinfo=UTC),
        source="command-test",
        source_version="b6",
        institution_id="REIS-OS",
        ocs_id="ÁGORA",
        project_id="COMMAND",
        run_id="run-b6",
        causation_id=f"cause-{sequence - 1}" if sequence > 1 else None,
        correlation_id="corr-b6",
        sequence=sequence,
        idempotency_key=f"idem-{sequence}",
        freshness=freshness,
        evidence_refs=(f"evidence-{sequence}",),
        payload={"sequence": sequence},
    )


def _store(tmp_path: Path, count: int = 3) -> CommandEventStore:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    for sequence in range(1, count + 1):
        store.append(_event(sequence))
    return store


def test_b6_reconnect_cursor_preserves_durable_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    feed = CommandRealtimeFeed(store, max_batch=2)

    first = feed.read(cursor=0)
    second = feed.read(cursor=first.next_cursor)

    assert [event.sequence for event in first.events] == [1, 2]
    assert first.next_cursor == 2
    assert [event.sequence for event in second.events] == [3]
    assert second.next_cursor == 3


def test_b6_backpressure_caps_batch_without_dropping_cursor(tmp_path: Path) -> None:
    feed = CommandRealtimeFeed(_store(tmp_path, count=3), max_batch=1)

    batches = [feed.read(cursor=index) for index in range(3)]

    assert [[event.sequence for event in batch.events] for batch in batches] == [
        [1],
        [2],
        [3],
    ]
    assert [batch.next_cursor for batch in batches] == [1, 2, 3]


def test_b6_empty_feed_is_unknown_not_live(tmp_path: Path) -> None:
    batch = CommandRealtimeFeed(CommandEventStore(tmp_path / "empty.sqlite3")).read()

    assert batch.events == ()
    assert batch.freshness is Freshness.UNKNOWN
    assert batch.disconnected is False


def test_b6_stale_event_makes_batch_explicitly_stale(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "stale.sqlite3")
    store.append(_event(1, Freshness.LIVE))
    store.append(_event(2, Freshness.STALE))

    batch = CommandRealtimeFeed(store).read()

    assert batch.freshness is Freshness.STALE


def test_b6_cursor_ahead_fails_closed(tmp_path: Path) -> None:
    feed = CommandRealtimeFeed(_store(tmp_path, count=1))

    with pytest.raises(ValueError, match="command_realtime_cursor_ahead"):
        feed.read(cursor=2)


def test_b6_sse_carries_sequence_freshness_and_causality(tmp_path: Path) -> None:
    batch = CommandRealtimeFeed(_store(tmp_path, count=1)).read()

    frames = list(encode_sse(batch))

    assert "id: 1" in frames[0]
    assert '"freshness":"live"' in frames[0]
    assert '"correlation_id":"corr-b6"' in frames[0]
    assert "event: command.cursor" in frames[-1]
    assert '"next_cursor": 1' in frames[-1]
