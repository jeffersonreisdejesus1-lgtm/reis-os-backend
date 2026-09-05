from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.command.event_store import CommandEventStore, EventStoreError
from app.command.events import CommandEvent, EventValidationError, Freshness
from app.command.projections import CommandProjector, canonical_projection


def event(
    *,
    event_id: str = "evt-1",
    sequence: int = 1,
    idempotency_key: str = "idem-1",
    ocs_id: str | None = "ÁGORA",
    projection: str = "ocs",
    data: dict[str, object] | None = None,
    evidence_refs: tuple[str, ...] = ("evidence://receipt/1",),
    payload_extra: dict[str, object] | None = None,
) -> CommandEvent:
    payload: dict[str, object] = {
        "projection": projection,
        "data": data or {"status": "executed"},
    }
    if payload_extra:
        payload.update(payload_extra)
    return CommandEvent(
        event_id=event_id,
        event_type="command.operation.updated",
        schema_version="1.0",
        occurred_at=datetime(2026, 9, 5, 4, 0, tzinfo=timezone.utc),
        source="reis-os-backend",
        source_version="ef926b0",
        institution_id="REIS-OS",
        ocs_id=ocs_id,
        project_id="COMMAND",
        run_id="run-b2",
        causation_id="cause-1",
        correlation_id="corr-1",
        sequence=sequence,
        idempotency_key=idempotency_key,
        freshness=Freshness.RECENT,
        evidence_refs=evidence_refs,
        payload=payload,
    )


def test_source_event_store_project_query_evidence_chain(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    source_event = event()

    assert store.append(source_event) is True
    stored = store.read_all()
    projection = CommandProjector().rebuild(stored)
    queried = projection.ocs["ÁGORA"]

    assert queried["status"] == "executed"
    assert queried["source"] == "reis-os-backend"
    assert queried["source_version"] == "ef926b0"
    assert queried["freshness"] == "recent"
    assert queried["evidence_refs"] == ["evidence://receipt/1"]


def test_replay_is_deterministic(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    assert store.append(event()) is True
    assert store.append(
        event(
            event_id="evt-2",
            sequence=2,
            idempotency_key="idem-2",
            projection="gate",
            data={"gate_id": "founder-merge", "status": "pending"},
        )
    ) is True

    projector = CommandProjector()
    first = canonical_projection(projector.rebuild(list(store.replay())))
    second = canonical_projection(projector.rebuild(list(store.replay())))
    assert first == second


def test_idempotent_replay_has_zero_material_duplication(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    source_event = event()
    assert store.append(source_event) is True
    assert store.append(source_event) is False
    assert len(store.read_all()) == 1


def test_idempotency_key_conflict_is_rejected(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    assert store.append(event()) is True
    with pytest.raises(EventStoreError, match="idempotency_conflict"):
        store.append(event(event_id="different", idempotency_key="idem-1"))


def test_sequence_gap_is_explicit_hold(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    with pytest.raises(EventValidationError, match="sequence_hold"):
        store.append(event(sequence=2))
    assert store.read_all() == []


def test_invalid_schema_fields_are_rejected(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "command-events.sqlite3")
    invalid = replace(event(), event_type="")
    with pytest.raises(EventValidationError, match="required_field_missing"):
        store.append(invalid)


def test_unknown_source_is_rejected(tmp_path: Path) -> None:
    unknown = replace(event(), source="unknown")
    with pytest.raises(EventValidationError, match="source_unknown"):
        CommandEventStore(tmp_path / "events.sqlite3").append(unknown)


def test_cross_ocs_contamination_is_rejected(tmp_path: Path) -> None:
    contaminated = event(payload_extra={"target_ocs_id": "SOFIA"})
    with pytest.raises(EventValidationError, match="cross_ocs_contamination"):
        CommandEventStore(tmp_path / "events.sqlite3").append(contaminated)


def test_verified_claim_requires_evidence(tmp_path: Path) -> None:
    unproven = event(
        evidence_refs=(),
        payload_extra={"claim_state": "verified"},
    )
    with pytest.raises(EventValidationError, match="claim_requires_evidence"):
        CommandEventStore(tmp_path / "events.sqlite3").append(unproven)


def test_no_data_system_health_remains_unknown() -> None:
    state = CommandProjector().rebuild([])
    assert state.system_health["status"] == "unknown"
    assert state.system_health["freshness"] == "unknown"


def test_health_without_evidence_cannot_be_promoted() -> None:
    health = event(
        projection="system_health",
        data={"status": "healthy"},
        evidence_refs=(),
    )
    state = CommandProjector().rebuild([health])
    assert state.system_health["status"] == "unknown"


def test_persistence_survives_store_reconstruction(tmp_path: Path) -> None:
    database = tmp_path / "command-events.sqlite3"
    first = CommandEventStore(database)
    assert first.append(event()) is True

    recovered = CommandEventStore(database)
    stored = recovered.read_all()
    assert len(stored) == 1
    assert stored[0].event_id == "evt-1"
    assert stored[0].evidence_refs == ("evidence://receipt/1",)
