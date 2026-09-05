from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.command.dossiers import CommandDossierService
from app.command.event_store import CommandEventStore
from app.command.events import CommandEvent, Freshness


def _event(ocs_id: str, sequence: int = 1) -> CommandEvent:
    return CommandEvent(
        event_id=f"evt-{ocs_id}-{sequence}",
        event_type="ocs.state.updated",
        schema_version="1",
        occurred_at=datetime(2026, 9, 5, 7, 0, tzinfo=UTC),
        source="command-runtime",
        source_version="b7",
        institution_id="REIS-OS",
        ocs_id=ocs_id,
        project_id="COMMAND",
        run_id=f"run-{ocs_id}",
        causation_id=None,
        correlation_id=f"corr-{ocs_id}",
        sequence=sequence,
        idempotency_key=f"idem-{ocs_id}-{sequence}",
        freshness=Freshness.RECENT,
        evidence_refs=(f"evidence-{ocs_id}",),
        payload={"status": "active"},
    )


def test_b7_exposes_exactly_ten_versioned_dossiers(tmp_path: Path) -> None:
    dossiers = CommandDossierService(tmp_path / "events.sqlite3").list()

    assert len(dossiers) == 10
    assert len({item["ocs_id"] for item in dossiers}) == 10
    assert all(item["version"].startswith("profile:") for item in dossiers)


def test_b7_capability_and_authority_are_separate_fields(tmp_path: Path) -> None:
    dossier = CommandDossierService(tmp_path / "events.sqlite3").get("agora")

    assert dossier is not None
    assert isinstance(dossier["capability"], list)
    assert isinstance(dossier["authority"], dict)
    assert "authority_envelope_ref" in dossier["authority"]
    assert dossier["capability"] != dossier["authority"]


def test_b7_no_runtime_event_is_unknown(tmp_path: Path) -> None:
    dossier = CommandDossierService(tmp_path / "events.sqlite3").get("noesis")

    assert dossier is not None
    assert dossier["current_state"]["status"] == "unknown"
    assert dossier["freshness"] == "unknown"
    assert dossier["source"]["runtime"] == "none"


def test_b7_runtime_state_is_bound_to_same_ocs_only(tmp_path: Path) -> None:
    store = CommandEventStore(tmp_path / "events.sqlite3")
    store.append(_event("ÁGORA"))

    service = CommandDossierService(tmp_path / "events.sqlite3")
    agora = service.get("agora")
    noesis = service.get("noesis")

    assert agora is not None and noesis is not None
    assert agora["current_state"]["status"] == "observed"
    assert agora["evidence_refs"] == ["evidence-ÁGORA"]
    assert noesis["current_state"]["status"] == "unknown"
    assert noesis["evidence_refs"] == []


def test_b7_dossier_includes_required_institutional_content(tmp_path: Path) -> None:
    dossier = CommandDossierService(tmp_path / "events.sqlite3").get("iris")

    assert dossier is not None
    for field in (
        "identity",
        "capability",
        "authority",
        "expertise",
        "current_state",
        "evidence_refs",
        "freshness",
        "source",
        "version",
        "institutional_relations",
    ):
        assert field in dossier
