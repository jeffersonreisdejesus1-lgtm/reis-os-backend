from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from app.governance_refactor.projections import (
    CandidateFilter,
    GovernanceCommandViews,
    GovernanceProjectionError,
)
from app.governance_refactor.scoped_store import ScopedGovernanceStore

NOW = datetime(2026, 9, 5, 22, 0, tzinfo=UTC)


@dataclass(frozen=True)
class MissionMetricsRecord:
    record_id: str
    mission_id: str
    ocs_id: str
    observed_at: datetime
    source_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    schema_version: str = "governance-candidate-v0.1"


def _schema(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE governance_candidate_records (
              position INTEGER PRIMARY KEY AUTOINCREMENT, record_type TEXT NOT NULL,
              record_id TEXT NOT NULL, schema_version TEXT NOT NULL,
              payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
              source_refs_json TEXT NOT NULL, provenance_refs_json TEXT NOT NULL,
              written_at TEXT NOT NULL);
            CREATE TABLE governance_candidate_events (
              position INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,
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


def _insert(
    path: Path,
    *,
    record_id: str,
    organization_id: str | None,
    observed_at: datetime = NOW,
    corrupt: bool = False,
) -> None:
    payload = {
        "record_id": record_id,
        "mission_id": "mission-1",
        "ocs_id": "SOFIA",
        "observed_at": observed_at.isoformat(),
        "source_refs": ["source:1"],
        "provenance_refs": ["proof:1"],
        "schema_version": "governance-candidate-v0.1",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = "0" * 64 if corrupt else sha256(encoded.encode()).hexdigest()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO governance_candidate_records VALUES(NULL,?,?,?,?,?,?,?,?)",
            (
                "MissionMetricsRecord", record_id, "governance-candidate-v0.1",
                encoded, digest, '["source:1"]', '["proof:1"]', NOW.isoformat(),
            ),
        )
        connection.execute(
            "INSERT INTO governance_candidate_events VALUES(NULL,?,?,?,?,?,?,?,?,?,?)",
            (
                "event-" + record_id, "MissionMetricsRecord", record_id,
                "governance-candidate-v0.1", "CANDIDATE_RECORD_APPENDED",
                digest, encoded, '["source:1"]', '["proof:1"]', NOW.isoformat(),
            ),
        )
        if organization_id is not None:
            connection.execute(
                "INSERT INTO governance_candidate_scopes VALUES(?,?,?,?,?)",
                (
                    organization_id, "MissionMetricsRecord", record_id,
                    "governance-candidate-v0.1", NOW.isoformat(),
                ),
            )


def test_r4_unavailable_is_unknown_not_healthy_or_zero(tmp_path: Path) -> None:
    result = GovernanceCommandViews(tmp_path / "missing.sqlite3").summary(
        organization_id="org-a"
    )
    assert result["source"]["health"] == "unavailable"
    assert result["total"] is None
    assert not result["epistemic_boundary"]["no_data_is_healthy"]
    assert not result["epistemic_boundary"]["unknown_is_zero"]


def test_r4_tenant_scope_and_legacy_records_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "candidates.sqlite3"
    _schema(path)
    _insert(path, record_id="owned-a", organization_id="org-a")
    _insert(path, record_id="legacy-unscoped", organization_id=None)
    view = GovernanceCommandViews(path)
    own = view.list_candidates(
        organization_id="org-a", filters=CandidateFilter(), cursor=0, limit=25,
        now=NOW,
    )
    foreign = view.list_candidates(
        organization_id="org-b", filters=CandidateFilter(), cursor=0, limit=25,
        now=NOW,
    )
    assert [item["record_id"] for item in own["items"]] == ["owned-a"]
    assert foreign["items"] == []
    with pytest.raises(GovernanceProjectionError, match="candidate_record_not_found"):
        view.get_candidate(
            organization_id="org-b", record_type="MissionMetricsRecord",
            record_id="owned-a", now=NOW,
        )


def test_r4_hash_readback_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    _schema(path)
    _insert(path, record_id="corrupt", organization_id="org-a", corrupt=True)
    with pytest.raises(GovernanceProjectionError, match="hash_mismatch"):
        GovernanceCommandViews(path).list_candidates(
            organization_id="org-a", filters=CandidateFilter(), cursor=0, limit=25,
            now=NOW,
        )


def test_r4_allowlist_cursor_filter_freshness_and_summary(tmp_path: Path) -> None:
    path = tmp_path / "valid.sqlite3"
    _schema(path)
    _insert(
        path,
        record_id="old",
        organization_id="org-a",
        observed_at=NOW - timedelta(hours=1),
    )
    _insert(path, record_id="new", organization_id="org-a")
    view = GovernanceCommandViews(path)
    page = view.list_candidates(
        organization_id="org-a",
        filters=CandidateFilter("MissionMetricsRecord", "mission-1", "SOFIA"),
        cursor=0,
        limit=1,
        now=NOW,
    )
    assert page["items"][0]["freshness"] == "stale"
    assert page["next_cursor"] == page["items"][0]["position"]
    second = view.list_candidates(
        organization_id="org-a", filters=CandidateFilter(),
        cursor=page["next_cursor"], limit=1, now=NOW,
    )
    assert second["items"][0]["freshness"] == "current"
    assert view.summary(organization_id="org-a")["total"] == 2
    with pytest.raises(GovernanceProjectionError, match="record_type_not_allowed"):
        view.list_candidates(
            organization_id="org-a", filters=CandidateFilter("NotAType"),
            cursor=0, limit=25,
        )


def test_r4_events_are_tenant_scoped_and_payload_not_duplicated(tmp_path: Path) -> None:
    path = tmp_path / "events.sqlite3"
    _schema(path)
    _insert(path, record_id="owned", organization_id="org-a")
    result = GovernanceCommandViews(path).events(
        organization_id="org-a", cursor=0, limit=10
    )
    assert result["count"] == 1
    assert "payload" not in result["items"][0]
    assert not result["source"]["duplicates_command_event_truth"]


def test_r4_atomic_writer_restart_readback_idempotency_and_conflicts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "writer.sqlite3"
    _schema(path)
    record = MissionMetricsRecord(
        "writer-1", "mission-1", "SOFIA", NOW, ("source:1",), ("proof:1",)
    )
    first = ScopedGovernanceStore(path).append(
        record, organization_id="org-a", occurred_at=NOW
    )
    replay = ScopedGovernanceStore(path).append(
        record, organization_id="org-a", occurred_at=NOW + timedelta(seconds=1)
    )
    assert not first["replayed"]
    assert replay["replayed"]
    assert GovernanceCommandViews(path).get_candidate(
        organization_id="org-a",
        record_type="MissionMetricsRecord",
        record_id="writer-1",
        now=NOW,
    )["payload_hash"] == first["payload_hash"]
    with pytest.raises(GovernanceProjectionError, match="scope_conflict"):
        ScopedGovernanceStore(path).append(
            record, organization_id="org-b", occurred_at=NOW
        )
    changed = MissionMetricsRecord(
        "writer-1", "mission-1", "SOFIA", NOW, ("source:2",), ("proof:1",)
    )
    with pytest.raises(GovernanceProjectionError, match="append_conflict"):
        ScopedGovernanceStore(path).append(
            changed, organization_id="org-a", occurred_at=NOW
        )
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM governance_candidate_records"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM governance_candidate_events"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM governance_candidate_scopes"
        ).fetchone()[0] == 1


def test_r4_tampered_evidence_and_unknown_type_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "evidence.sqlite3"
    _schema(path)
    _insert(path, record_id="owned", organization_id="org-a")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE governance_candidate_records SET source_refs_json='[]'"
        )
    with pytest.raises(GovernanceProjectionError, match="evidence_envelope"):
        GovernanceCommandViews(path).list_candidates(
            organization_id="org-a",
            filters=CandidateFilter(),
            cursor=0,
            limit=25,
            now=NOW,
        )

    other = tmp_path / "unknown.sqlite3"
    _schema(other)
    _insert(other, record_id="hidden", organization_id="org-a")
    with sqlite3.connect(other) as connection:
        connection.execute(
            "UPDATE governance_candidate_records SET record_type='InjectedType'"
        )
        connection.execute(
            "UPDATE governance_candidate_events SET record_type='InjectedType'"
        )
        connection.execute(
            "UPDATE governance_candidate_scopes SET record_type='InjectedType'"
        )
    view = GovernanceCommandViews(other)
    assert view.summary(organization_id="org-a")["total"] == 0
    assert view.events(organization_id="org-a", cursor=0, limit=25)["count"] == 0
