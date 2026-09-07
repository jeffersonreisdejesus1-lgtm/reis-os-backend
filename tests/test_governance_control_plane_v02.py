from __future__ import annotations

from pathlib import Path

import pytest

from app.governance_plane import (
    AssuranceRecord,
    AssuranceVerdict,
    CapabilityHealth,
    CapabilityKind,
    CapabilityRecord,
    CommandGovernanceProjection,
    EvidenceCompleteness,
    EvidenceFreshness,
    EvidenceRef,
    FounderDecision,
    FounderDecisionValue,
    GovernanceLedger,
    GovernanceService,
    MetricObservation,
    QualityAssessment,
    QualityVerdict,
    ReadinessStatus,
)


def service(tmp_path: Path) -> GovernanceService:
    return GovernanceService(GovernanceLedger(tmp_path / "governance.sqlite3"))


def evidence(object_ref: str = "pr:57") -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev:1",
        object_ref=object_ref,
        source_ref="github:pr57:head",
        source_hash="sha256:abc",
        observed_at="2026-09-07T03:00:00Z",
        completeness=EvidenceCompleteness.COMPLETE,
        freshness=EvidenceFreshness.FRESH,
    )


def test_quality_pass_without_existing_evidence_is_non_promotable(tmp_path):
    s = service(tmp_path)
    with pytest.raises(ValueError, match="quality_pass_requires_existing_evidence"):
        s.add_quality_assessment(
            QualityAssessment(
                assessment_id="qa:missing",
                object_ref="pr:57",
                domain="architecture",
                applicable=True,
                verdict=QualityVerdict.PASS,
                assessor_ref="AGORA",
                evidence_ids=("ev:missing",),
            )
        )


def test_assurance_pass_without_existing_evidence_is_rejected(tmp_path):
    s = service(tmp_path)
    with pytest.raises(ValueError, match="assurance_pass_requires_existing_evidence"):
        s.add_assurance(
            AssuranceRecord(
                assurance_id="as:missing",
                object_ref="pr:57",
                assurer_ref="GROK",
                verdict=AssuranceVerdict.PASS,
                evidence_ids=("ev:missing",),
            )
        )


def test_readiness_requires_fresh_complete_evidence_quality_and_assurance(tmp_path):
    s = service(tmp_path)
    s.add_evidence(evidence())
    s.add_quality_assessment(
        QualityAssessment(
            assessment_id="qa:1",
            object_ref="pr:57",
            domain="architecture",
            applicable=True,
            verdict=QualityVerdict.PASS_WITH_RESERVATIONS,
            assessor_ref="AGORA",
            evidence_ids=("ev:1",),
            reservations=("local_worker_boundary",),
        )
    )
    s.add_assurance(
        AssuranceRecord(
            assurance_id="as:1",
            object_ref="pr:57",
            assurer_ref="GROK_FEDERATED_ASSURANCE_SEAT",
            verdict=AssuranceVerdict.PASS_WITH_RESERVATIONS,
            evidence_ids=("ev:1",),
            findings=("live_provider_not_proven",),
        )
    )
    ready = s.derive_readiness(readiness_id="ready:1", object_ref="pr:57", assurance_required=True)
    assert ready.status is ReadinessStatus.READY_FOR_FOUNDER_REVIEW
    assert ready.reservations == ("local_worker_boundary",)


def test_metrics_never_create_readiness_or_founder_decision(tmp_path):
    s = service(tmp_path)
    s.add_metric(
        MetricObservation(
            metric_id="metric:fast",
            object_ref="pr:57",
            metric_name="elapsed_seconds",
            value=1,
            source_ref="clock:system",
            measurement_method="system_timestamp",
            measurement_version="v1",
            observed_at="2026-09-07T03:00:00Z",
            window="mission",
            completeness=EvidenceCompleteness.COMPLETE,
        )
    )
    result = s.derive_readiness(readiness_id="ready:metric", object_ref="pr:57", assurance_required=False)
    assert result.status is ReadinessStatus.NOT_READY
    assert "evidence_incomplete_or_stale" in result.open_blockers
    assert "quality_assessment_missing" in result.open_blockers


def test_metric_without_source_must_remain_unknown(tmp_path):
    s = service(tmp_path)
    with pytest.raises(ValueError, match="metric_without_source_must_be_unknown"):
        s.add_metric(
            MetricObservation(
                metric_id="metric:unsourced",
                object_ref="pr:57",
                metric_name="elapsed_seconds",
                value=1,
                source_ref=None,
                measurement_method="unknown",
                measurement_version="v1",
                observed_at="2026-09-07T03:00:00Z",
                window="mission",
                completeness=EvidenceCompleteness.COMPLETE,
            )
        )


def test_founder_decision_requires_explicit_founder_actor_and_readiness(tmp_path):
    s = service(tmp_path)
    s.derive_readiness(readiness_id="ready:not-ready", object_ref="pr:57", assurance_required=False)
    decision = FounderDecision(
        decision_id="founder:1",
        object_ref="pr:57",
        decision=FounderDecisionValue.HOLD,
        founder_actor_ref="FOUNDER",
        decided_at="2026-09-07T03:05:00Z",
    )
    with pytest.raises(PermissionError, match="founder_decision_requires_explicit_founder_actor"):
        s.record_founder_decision(decision, actor_role="NOESIS")
    s.record_founder_decision(decision, actor_role="FOUNDER")
    records = s.ledger.records(object_ref="pr:57", record_type="FOUNDER_DECISION")
    assert len(records) == 1


def test_founder_cannot_approve_release_when_readiness_is_not_ready(tmp_path):
    s = service(tmp_path)
    s.derive_readiness(readiness_id="ready:not-ready", object_ref="pr:57", assurance_required=True)
    with pytest.raises(ValueError, match="founder_approval_requires_ready_for_review"):
        s.record_founder_decision(
            FounderDecision(
                decision_id="founder:approve-too-early",
                object_ref="pr:57",
                decision=FounderDecisionValue.APPROVE_FOR_RELEASE,
                founder_actor_ref="FOUNDER",
                decided_at="2026-09-07T03:05:00Z",
            ),
            actor_role="FOUNDER",
        )


def test_governance_records_are_idempotent_but_divergence_conflicts(tmp_path):
    s = service(tmp_path)
    ev = evidence()
    s.add_evidence(ev)
    s.add_evidence(ev)
    with pytest.raises(ValueError, match="governance_idempotency_conflict"):
        s.add_evidence(
            EvidenceRef(
                evidence_id=ev.evidence_id,
                object_ref=ev.object_ref,
                source_ref=ev.source_ref,
                source_hash="sha256:different",
                observed_at=ev.observed_at,
                completeness=ev.completeness,
                freshness=ev.freshness,
            )
        )


def test_capability_projection_does_not_treat_label_as_live_connectivity(tmp_path):
    s = service(tmp_path)
    s.put_capability(
        CapabilityRecord(
            capability_id="seat:grok",
            provider="xAI",
            kind=CapabilityKind.FEDERATED_SEAT,
            seat="GROK",
            integration_ref=None,
            can_read=True,
            can_write=False,
            can_model_invoke=True,
            connection_validated=False,
            machine_receipt_supported=False,
            source_of_truth_role=None,
            health=CapabilityHealth.UNKNOWN,
            observed_at="2026-09-07T03:00:00Z",
            capability_version="v1",
        )
    )
    view = CommandGovernanceProjection(s.ledger).capability_view()
    assert view["summary"]["total"] == 1
    assert view["summary"]["validated"] == 0
    assert view["summary"]["model_invokable"] == 0


def test_command_projection_is_read_only_surface(tmp_path):
    s = service(tmp_path)
    projection = CommandGovernanceProjection(s.ledger)
    assert not hasattr(projection, "add_evidence")
    assert not hasattr(projection, "record_founder_decision")
    assert not hasattr(projection, "put_capability")
