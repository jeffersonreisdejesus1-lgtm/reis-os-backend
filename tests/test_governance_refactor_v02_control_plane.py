from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.governance_refactor.contracts import CapabilityClass, IntegrationCapabilityRecord
from app.governance_refactor.projections import GovernanceCommandViews
from app.governance_refactor.scoped_store import ScopedGovernanceStore
from app.main import app

NOW = datetime(2026, 9, 7, 3, 45, tzinfo=UTC)


def _schema(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE governance_candidate_records (
              position INTEGER PRIMARY KEY, record_type TEXT NOT NULL,
              record_id TEXT NOT NULL, schema_version TEXT NOT NULL,
              payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
              source_refs_json TEXT NOT NULL, provenance_refs_json TEXT NOT NULL,
              written_at TEXT NOT NULL,
              UNIQUE(record_type, record_id, schema_version));
            CREATE TABLE governance_candidate_events (
              position INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
              record_type TEXT NOT NULL, record_id TEXT NOT NULL,
              schema_version TEXT NOT NULL, event_type TEXT NOT NULL,
              payload_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
              source_refs_json TEXT NOT NULL, provenance_refs_json TEXT NOT NULL,
              occurred_at TEXT NOT NULL);
            CREATE TABLE governance_candidate_scopes (
              organization_id TEXT NOT NULL, record_type TEXT NOT NULL,
              record_id TEXT NOT NULL, schema_version TEXT NOT NULL,
              bound_at TEXT NOT NULL,
              PRIMARY KEY (organization_id, record_type, record_id, schema_version),
              UNIQUE (record_type, record_id, schema_version));
            """
        )


def _record(
    integration_id: str,
    *,
    provider: str,
    seat: str,
    source_access: bool,
    live_model: bool,
) -> IntegrationCapabilityRecord:
    return IntegrationCapabilityRecord(
        integration_id=integration_id,
        provider=provider,
        category="federated-seat",
        purpose="federated execution / assurance",
        connection_status="CONNECTED",
        validation_status="VALIDATED" if source_access or live_model else "PARTIAL",
        read_capabilities=("source",) if source_access else (),
        write_capabilities=(),
        supported_artifacts=("source", "receipt"),
        authentication_boundary="seat-session",
        canonical_source_role=None,
        primary_ocs_users=("NOESIS",),
        authorized_use_cases=("assurance",),
        prohibited_use_cases=("promotion",),
        known_limitations=() if live_model else ("live_model_adapter_unavailable",),
        security_risks=(),
        data_risks=(),
        reversibility="REVERSIBLE",
        evidence_capability="MACHINE_RECEIPT" if live_model else "SOURCE_READ",
        last_validated_at=NOW,
        capability_version="v02",
        source_links=(),
        provenance_refs=(f"receipt:{integration_id}",),
        capability_class=CapabilityClass.FEDERATED_SEAT,
        seat_ref=seat,
        host_ref=provider,
        model_invoke_capabilities=("model.invoke",) if live_model else (),
        source_access_status="AVAILABLE" if source_access else "UNAVAILABLE",
        live_model_invocation_status="AVAILABLE" if live_model else "UNAVAILABLE",
        host_adapter_available=live_model,
        machine_verifiable_receipt=live_model,
        source_access_validated=source_access,
    )


def test_control_plane_capability_projection_separates_source_and_model_access(
    tmp_path: Path,
) -> None:
    path = tmp_path / "governance.sqlite3"
    _schema(path)
    writer = ScopedGovernanceStore(path)
    writer.append(
        _record(
            "seat:grok",
            provider="xAI",
            seat="GROK",
            source_access=True,
            live_model=False,
        ),
        organization_id="org-a",
        occurred_at=NOW,
    )
    writer.append(
        _record(
            "seat:controlled-worker",
            provider="REIS_OS",
            seat="CONTROLLED_WORKER",
            source_access=False,
            live_model=True,
        ),
        organization_id="org-a",
        occurred_at=NOW,
    )

    view = GovernanceCommandViews(path).capability_health(
        organization_id="org-a", now=NOW
    )
    assert view["summary"] == {
        "total": 2,
        "federated_seats": 2,
        "source_access_validated": 1,
        "host_adapters_available": 1,
        "live_model_invokable": 1,
        "machine_receipt_supported": 1,
    }
    grok = next(item for item in view["items"] if item["record_id"] == "seat:grok")
    assert grok["payload"]["source_access_validated"] is True
    assert grok["payload"]["live_model_invocation_status"] == "UNAVAILABLE"
    assert view["epistemic_boundary"]["candidate_is_authority"] is False


def test_capability_projection_is_tenant_scoped_and_unknown_is_not_zero(
    tmp_path: Path,
) -> None:
    missing = GovernanceCommandViews(tmp_path / "missing.sqlite3").capability_health(
        organization_id="org-a"
    )
    assert missing["summary"]["total"] is None
    assert missing["summary"]["live_model_invokable"] is None
    assert missing["source"]["health"] == "unavailable"

    path = tmp_path / "tenant.sqlite3"
    _schema(path)
    ScopedGovernanceStore(path).append(
        _record(
            "seat:grok",
            provider="xAI",
            seat="GROK",
            source_access=True,
            live_model=False,
        ),
        organization_id="org-a",
        occurred_at=NOW,
    )
    foreign = GovernanceCommandViews(path).capability_health(
        organization_id="org-b", now=NOW
    )
    assert foreign["summary"]["total"] == 0
    assert foreign["items"] == []


def test_command_capability_endpoint_is_read_only_get_surface() -> None:
    matching = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/v1/command/governance/capabilities"
    ]
    assert len(matching) == 1
    assert matching[0].methods == {"GET"}
