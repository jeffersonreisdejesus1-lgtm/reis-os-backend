from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.governance_refactor.contracts import (
    SCHEMA_VERSION,
    AgentAvailabilityContract,
    AuxiliaryAgentEvidenceContract,
    AvailabilityState,
    ChatInstitutionalRoutingContract,
    Completeness,
    FounderApprovalDecision,
    FounderDecision,
    GatePerformanceRecord,
    GateVerdict,
    IntegrationCapabilityRecord,
    MissionMetricsRecord,
    PromotionReadinessState,
    QualityApplicabilityMatrix,
    QualityDomainAssessment,
    QualityEvidenceBundle,
    QualityVerdict,
    Readiness,
    RefactorClass,
    RefactorEvent,
    RoutingState,
    SourceLink,
)
from app.governance_refactor.store import (
    GovernanceCandidateStore,
    GovernancePersistenceError,
)

NOW = datetime(2026, 9, 5, 19, 30, tzinfo=UTC)
SOURCE = (SourceLink("github", "commit:abc", "technical_provenance"),)


def _apply_candidate_schema_0004(path: Path) -> None:
    """Test fixture standing in for the external Alembic-owned physical schema."""
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE governance_candidate_records (
                position INTEGER PRIMARY KEY AUTOINCREMENT,
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                provenance_refs_json TEXT NOT NULL,
                written_at TEXT NOT NULL,
                UNIQUE(record_type, record_id, schema_version)
            );
            CREATE INDEX ix_governance_candidate_records_type_id
            ON governance_candidate_records(record_type, record_id);
            CREATE TABLE governance_candidate_events (
                position INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                provenance_refs_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            CREATE INDEX ix_governance_candidate_events_record
            ON governance_candidate_events(record_type, record_id, position);
            """
        )


def _schema_snapshot(path: Path) -> tuple[tuple[str, str, str], ...]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE name LIKE 'governance_candidate_%'
               OR name LIKE 'ix_governance_candidate_%'
            ORDER BY type, name
            """
        ).fetchall()
    return tuple((str(row[0]), str(row[1]), str(row[2])) for row in rows)


def metric(**changes: object) -> MissionMetricsRecord:
    baseline = MissionMetricsRecord(
        record_id="metric-1",
        mission_id="mission-1",
        ocs_id="SOFIA",
        product_id=None,
        gate_id=None,
        started_at=NOW - timedelta(minutes=5),
        completed_at=NOW,
        active_execution_seconds=240,
        waiting_seconds=60,
        founder_wait_seconds=0,
        external_wait_seconds=0,
        retries=0,
        failures=0,
        refactors=0,
        founder_interventions=0,
        autonomous_completion=True,
        source_refs=("commit:abc",),
        source_links=SOURCE,
        provenance_refs=("ci:1",),
        measurement_method="system_timestamp",
        measurement_version="v0.1",
        observed_at=NOW,
        completeness=Completeness.COMPLETE,
    )
    return replace(baseline, **changes)


def test_r2_freezes_all_candidate_schema_types() -> None:
    names = {
        MissionMetricsRecord.__name__,
        GatePerformanceRecord.__name__,
        QualityApplicabilityMatrix.__name__,
        QualityDomainAssessment.__name__,
        QualityEvidenceBundle.__name__,
        PromotionReadinessState.__name__,
        FounderApprovalDecision.__name__,
        RefactorEvent.__name__,
        IntegrationCapabilityRecord.__name__,
        AgentAvailabilityContract.__name__,
        ChatInstitutionalRoutingContract.__name__,
        AuxiliaryAgentEvidenceContract.__name__,
    }
    assert len(names) == 12
    assert SCHEMA_VERSION == "governance-candidate-v0.1"


def test_metric_unknown_and_validation_semantics() -> None:
    assert metric().promotable_measurement(NOW + timedelta(seconds=1))
    future = metric(observed_at=NOW + timedelta(hours=1))
    assert future.effective_completeness(NOW) is Completeness.UNKNOWN
    assert not future.promotable_measurement(NOW)
    assert not metric(source_refs=()).promotable_measurement(NOW)
    with pytest.raises(ValueError, match="negative_candidate_measurement"):
        metric(active_execution_seconds=-1)


def test_quality_and_promotion_do_not_self_promote() -> None:
    assessment = QualityDomainAssessment(
        assessment_id="assessment-1",
        product_id="product-1",
        baseline_ref="baseline-1",
        domain="security",
        applicable=False,
        applicability_reason="not in bounded scope",
        assessor_ocs="AGORA",
        evidence_refs=(),
        source_links=SOURCE,
        provenance_refs=(),
        findings=(),
        verdict=QualityVerdict.NOT_APPLICABLE,
        assessed_at=NOW,
        assessment_version="v0.1",
    )
    assert not assessment.applicable
    readiness = PromotionReadinessState(
        readiness_id="ready-1",
        product_id="product-1",
        baseline_ref="baseline-1",
        required_domains=("backend",),
        completed_assessments=("assessment-2",),
        open_blockers=(),
        assurance_state="ASSURED",
        readiness=Readiness.READY_FOR_FOUNDER_REVIEW,
        evidence_bundle_ref="bundle-1",
        derived_from=("assessment-2",),
        source_links=SOURCE,
        provenance_refs=("assurance:1",),
        derivation_version="v0.1",
        derived_at=NOW,
    )
    assert not readiness.releases_product
    with pytest.raises(ValueError, match="required_candidate_field_missing"):
        FounderApprovalDecision(
            decision_id="decision-1",
            product_id="product-1",
            baseline_ref="baseline-1",
            evidence_bundle_ref="bundle-1",
            decision=FounderDecision.APPROVE_FOR_RELEASE,
            reservations=(),
            authority_ref="founder-authority",
            decided_at=NOW,
            explicit_founder_act_ref="",
            source_links=SOURCE,
            provenance_refs=(),
        )


def test_agent_and_chat_claim_boundaries_fail_closed() -> None:
    with pytest.raises(ValueError, match="recoverable_requires_proof_ref"):
        AgentAvailabilityContract(
            contract_id="availability-1",
            ocs_id="SOFIA",
            availability_state=AvailabilityState.RECOVERABLE,
            current_instance_id="instance-1",
            generation=1,
            mission_bound=True,
            lease_status="VALID",
            recovery_ready=True,
            recovery_proof_ref=None,
            auxiliary_spawn=False,
            chat_addressable=True,
            last_checkpoint_ref="checkpoint-1",
            last_readback_ref="readback-1",
            evidence_state=Completeness.COMPLETE,
            freshness_at=NOW,
            source_links=SOURCE,
            provenance_refs=("proof:1",),
            contract_version="v0.1",
        )
    with pytest.raises(ValueError, match="chat_native_execution_unproven"):
        ChatInstitutionalRoutingContract(
            route_id="route-1",
            addressed_ocs_id="SOFIA",
            mission_id="mission-1",
            resolved_instance_id="instance-1",
            generation=1,
            routing_state=RoutingState.ADDRESSABLE,
            route_receipt_ref="receipt-1",
            response_correlation_id="corr-1",
            chat_addressable=True,
            chat_native_execution=True,
            source_links=SOURCE,
            provenance_refs=("receipt-1",),
            contract_version="v0.1",
        )
    with pytest.raises(ValueError, match="auxiliary_authority_escapes_parent"):
        AuxiliaryAgentEvidenceContract(
            evidence_id="aux-1",
            parent_ocs_id="SOFIA",
            auxiliary_id="helper-1",
            mission_id="mission-1",
            requested_scope=("write", "promote"),
            parent_authority_scope=("write",),
            produced_evidence_refs=(),
            created_new_ocs_identity=False,
            source_links=SOURCE,
            provenance_refs=(),
            contract_version="v0.1",
        )


def test_r3_r01_missing_0004_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "revision-0003.sqlite3"
    database.touch()
    with pytest.raises(
        GovernancePersistenceError,
        match="governance_candidate_migration_0004_required",
    ):
        GovernanceCandidateStore(database)


def test_r3_r02_migrated_0004_allows_store_startup(tmp_path: Path) -> None:
    database = tmp_path / "revision-0004.sqlite3"
    _apply_candidate_schema_0004(database)
    store = GovernanceCandidateStore(database)
    assert store.event_count() == 0


def test_r3_r03_repeated_store_startup_does_not_mutate_schema(tmp_path: Path) -> None:
    database = tmp_path / "stable-schema.sqlite3"
    _apply_candidate_schema_0004(database)
    before = _schema_snapshot(database)
    GovernanceCandidateStore(database)
    GovernanceCandidateStore(database)
    assert _schema_snapshot(database) == before


def test_r3_r04_downgrade_is_explicitly_destructive() -> None:
    migration = Path("migrations/versions/0004_governance_candidate_records.py")
    source = migration.read_text(encoding="utf-8")
    assert "No data-preserving rollback claim" in source
    assert "Destructive by design" in source


def test_r3_append_readback_replay_and_conflict(tmp_path: Path) -> None:
    database = tmp_path / "governance.sqlite3"
    _apply_candidate_schema_0004(database)
    store = GovernanceCandidateStore(database)
    written = store.append(metric(), occurred_at=NOW)
    assert written["record_id"] == "metric-1"
    assert written["payload"]["measurement_method"] == "system_timestamp"
    assert written["source_refs"] == ["commit:abc"]
    assert written["provenance_refs"] == ["ci:1"]
    assert store.event_count() == 1

    replayed = store.append(metric(), occurred_at=NOW + timedelta(seconds=1))
    assert replayed["payload_hash"] == written["payload_hash"]
    assert store.event_count() == 1

    events = store.replay()
    assert len(events) == 1
    assert events[0]["payload_hash"] == written["payload_hash"]
    assert events[0]["event_type"] == "CANDIDATE_RECORD_APPENDED"

    with pytest.raises(GovernancePersistenceError, match="candidate_append_conflict"):
        store.append(metric(retries=1), occurred_at=NOW + timedelta(seconds=2))


def test_r3_r05_multi_store_exact_duplicate_converges(tmp_path: Path) -> None:
    database = tmp_path / "race.sqlite3"
    _apply_candidate_schema_0004(database)
    first = GovernanceCandidateStore(database)
    second = GovernanceCandidateStore(database)

    def append(store: GovernanceCandidateStore) -> str:
        result = store.append(metric(), occurred_at=NOW)
        return str(result["payload_hash"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        hashes = list(executor.map(append, (first, second)))

    assert len(set(hashes)) == 1
    assert first.event_count() == 1


def test_version_mismatch_is_explicit(tmp_path: Path) -> None:
    database = tmp_path / "version.sqlite3"
    _apply_candidate_schema_0004(database)
    store = GovernanceCandidateStore(database)
    incompatible = metric(schema_version="governance-candidate-v9")
    with pytest.raises(
        GovernancePersistenceError,
        match="candidate_schema_version_incompatible",
    ):
        store.append(incompatible, occurred_at=NOW)


def test_contract_examples_are_constructible() -> None:
    gate = GatePerformanceRecord(
        gate_id="gate-1",
        object_ref="object-1",
        gate_class="technical",
        opened_at=NOW,
        closed_at=None,
        elapsed_seconds=None,
        blocking_seconds=None,
        owner_ocs="SOFIA",
        verifier_ocs="AGORA",
        assurance_required=False,
        evidence_refs=(),
        source_links=SOURCE,
        provenance_refs=(),
        blockers=(),
        findings=(),
        verdict=GateVerdict.OPEN,
        routing_result=None,
        version="v0.1",
    )
    matrix = QualityApplicabilityMatrix(
        matrix_id="matrix-1",
        object_ref="object-1",
        domain="backend",
        applicable=True,
        reason="backend changed",
        required_evidence=("ci",),
        mandatory_for_promotion=True,
        source_links=SOURCE,
        provenance_refs=(),
        version="v0.1",
    )
    bundle = QualityEvidenceBundle(
        bundle_id="bundle-1",
        baseline_ref="baseline-1",
        evidence_refs=("ci:1",),
        provenance_refs=("commit:abc",),
        source_links=SOURCE,
        assessment_refs=("assessment-1",),
        assurance_refs=(),
        known_limitations=(),
        evidence_completeness=Completeness.PARTIAL,
        created_at=NOW,
        bundle_version="v0.1",
    )
    refactor = RefactorEvent(
        refactor_id="refactor-1",
        object_ref="object-1",
        refactor_class=RefactorClass.QUALITY_REFACTOR,
        reason="tighten evidence semantics",
        discovered_at_stage="R3",
        affected_contracts=("MissionMetricsRecord",),
        started_at=NOW,
        completed_at=None,
        elapsed_seconds=None,
        recurrence_ref=None,
        evidence_refs=(),
        source_links=SOURCE,
        provenance_refs=(),
        learning_ref=None,
        event_version="v0.1",
    )
    integration = IntegrationCapabilityRecord(
        integration_id="github",
        provider="GitHub",
        category="CODE_AND_PROVENANCE",
        purpose="code truth",
        connection_status="CONNECTED",
        validation_status="VALIDATED",
        read_capabilities=("read",),
        write_capabilities=("write",),
        supported_artifacts=("code", "ci"),
        authentication_boundary="connector",
        canonical_source_role="CODE_TRUTH",
        primary_ocs_users=("SOFIA",),
        authorized_use_cases=("implementation",),
        prohibited_use_cases=("authority_grant",),
        known_limitations=(),
        security_risks=(),
        data_risks=(),
        reversibility="bounded",
        evidence_capability="receipt_readback",
        last_validated_at=NOW,
        capability_version="v0.1",
        source_links=SOURCE,
        provenance_refs=("connector:github",),
    )
    assert gate.verdict is GateVerdict.OPEN
    assert matrix.applicable
    assert bundle.evidence_completeness is Completeness.PARTIAL
    assert refactor.refactor_class is RefactorClass.QUALITY_REFACTOR
    assert integration.canonical_source_role == "CODE_TRUTH"
