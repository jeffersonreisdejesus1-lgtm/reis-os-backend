from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness
from app.command.observability import CommandObservability


def _event(
    sequence: int,
    *,
    event_type: str = "request.received",
    kind: str | None = None,
    freshness: Freshness = Freshness.RECENT,
    latency_ms: float | None = None,
) -> CommandEvent:
    payload: dict[str, object] = {}
    if kind is not None:
        payload["observability_kind"] = kind
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    return CommandEvent(
        event_id=f"evt-{sequence}",
        event_type=event_type,
        schema_version="1",
        occurred_at=datetime(2026, 9, 5, 8, sequence, tzinfo=UTC),
        source="command-observability-test",
        source_version="b8",
        institution_id="REIS-OS",
        ocs_id="ÁGORA",
        project_id="COMMAND",
        run_id="run-b8",
        causation_id=f"cause-{sequence}",
        correlation_id="corr-b8",
        sequence=sequence,
        idempotency_key=f"idem-{sequence}",
        freshness=freshness,
        evidence_refs=(f"evidence-{sequence}",),
        payload=payload,
    )


def test_b8_no_data_is_unknown_not_zero_or_healthy(tmp_path: Path) -> None:
    snapshot = CommandObservability(tmp_path / "empty.sqlite3").snapshot()

    assert snapshot["status"] == "no_data"
    assert snapshot["event_count"] is None
    assert snapshot["health"] == "unknown"
    assert snapshot["freshness"] == "unknown"
    assert snapshot["latency_ms"] == {"min": None, "max": None, "avg": None}


def test_b8_correlates_required_surfaces_from_events(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    store.append(_event(1, kind="request", latency_ms=10.0))
    store.append(_event(2, kind="decision", latency_ms=20.0))
    store.append(_event(3, kind="receipt", latency_ms=30.0))
    store.append(_event(4, kind="error", event_type="command.error"))

    snapshot = CommandObservability(tmp_path / "events.sqlite3").snapshot()

    assert snapshot["event_count"] == 4
    assert snapshot["run_ids"] == ["run-b8"]
    assert snapshot["project_ids"] == ["COMMAND"]
    assert snapshot["ocs_ids"] == ["ÁGORA"]
    assert len(snapshot["requests"]) == 1
    assert len(snapshot["decisions"]) == 1
    assert len(snapshot["receipts"]) == 1
    assert len(snapshot["errors"]) == 1
    assert snapshot["latency_ms"] == {"min": 10.0, "max": 30.0, "avg": 20.0}
    assert snapshot["health"] == "degraded"
    assert snapshot["correlation_ids"] == ["corr-b8"]


def test_b8_absent_latency_remains_unknown(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    store.append(_event(1))

    snapshot = CommandObservability(tmp_path / "events.sqlite3").snapshot()

    assert snapshot["latency_ms"]["avg"] is None
    assert snapshot["health"] == "observed_no_error_event"


def test_b8_stale_is_never_current(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    store.append(_event(1, freshness=Freshness.LIVE))
    store.append(_event(2, freshness=Freshness.STALE))

    snapshot = CommandObservability(tmp_path / "events.sqlite3").snapshot()

    assert snapshot["freshness"] == "stale"


def test_b8_preserves_causation_and_evidence(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    store.append(_event(1, kind="receipt"))

    snapshot = CommandObservability(tmp_path / "events.sqlite3").snapshot()
    event = snapshot["events"][0]

    assert snapshot["causation_ids"] == ["cause-1"]
    assert event["correlation_id"] == "corr-b8"
    assert event["evidence_refs"] == ["evidence-1"]
