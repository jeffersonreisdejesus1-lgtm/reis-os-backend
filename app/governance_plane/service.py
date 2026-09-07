from __future__ import annotations

from .contracts import (
    AssuranceRecord,
    CapabilityRecord,
    EvidenceCompleteness,
    EvidenceFreshness,
    EvidenceRef,
    FounderDecision,
    MetricObservation,
    PromotionReadiness,
    QualityAssessment,
    QualityVerdict,
    ReadinessStatus,
    RefactorEvent,
)
from .store import GovernanceLedger


class GovernanceService:
    def __init__(self, ledger: GovernanceLedger) -> None:
        self.ledger = ledger

    def add_evidence(self, record: EvidenceRef) -> None:
        self.ledger.append(record_type="EVIDENCE", record_id=record.evidence_id, object_ref=record.object_ref, record=record)

    def add_quality_assessment(self, record: QualityAssessment) -> None:
        if record.applicable and not record.evidence_ids and record.verdict in {
            QualityVerdict.PASS,
            QualityVerdict.PASS_WITH_RESERVATIONS,
        }:
            raise ValueError("quality_pass_requires_evidence")
        self.ledger.append(record_type="QUALITY", record_id=record.assessment_id, object_ref=record.object_ref, record=record)

    def add_assurance(self, record: AssuranceRecord) -> None:
        if record.verdict.value.startswith("PASS") and not record.evidence_ids:
            raise ValueError("assurance_pass_requires_evidence")
        self.ledger.append(record_type="ASSURANCE", record_id=record.assurance_id, object_ref=record.object_ref, record=record)

    def add_metric(self, record: MetricObservation) -> None:
        self.ledger.append(record_type="METRIC", record_id=record.metric_id, object_ref=record.object_ref, record=record)

    def add_refactor_event(self, record: RefactorEvent) -> None:
        self.ledger.append(record_type="REFACTOR", record_id=record.refactor_id, object_ref=record.object_ref, record=record)

    def put_capability(self, record: CapabilityRecord) -> None:
        self.ledger.upsert_capability(record)

    def derive_readiness(self, *, readiness_id: str, object_ref: str, assurance_required: bool) -> PromotionReadiness:
        records = self.ledger.records(object_ref=object_ref)
        evidences = [r["payload"] for r in records if r["record_type"] == "EVIDENCE"]
        quality = [r["payload"] for r in records if r["record_type"] == "QUALITY"]
        assurance = [r["payload"] for r in records if r["record_type"] == "ASSURANCE"]

        evidence_complete = bool(evidences) and all(
            e["completeness"] == EvidenceCompleteness.COMPLETE.value
            and e["freshness"] == EvidenceFreshness.FRESH.value
            for e in evidences
        )
        blockers: list[str] = []
        reservations: list[str] = []

        if not evidence_complete:
            blockers.append("evidence_incomplete_or_stale")

        applicable = [q for q in quality if q["applicable"]]
        if not applicable:
            blockers.append("quality_assessment_missing")
        for assessment in applicable:
            verdict = assessment["verdict"]
            if verdict in {QualityVerdict.HOLD.value, QualityVerdict.UNKNOWN.value}:
                blockers.append(f"quality:{assessment['assessment_id']}:{verdict}")
            reservations.extend(assessment.get("reservations", []))

        assurance_satisfied = not assurance_required or any(
            a["verdict"] in {"PASS", "PASS_WITH_RESERVATIONS"} for a in assurance
        )
        if assurance_required and not assurance_satisfied:
            blockers.append("assurance_required_not_satisfied")

        status = ReadinessStatus.READY_FOR_FOUNDER_REVIEW if not blockers else ReadinessStatus.NOT_READY
        result = PromotionReadiness(
            readiness_id=readiness_id,
            object_ref=object_ref,
            status=status,
            evidence_complete=evidence_complete,
            open_blockers=tuple(sorted(set(blockers))),
            reservations=tuple(sorted(set(reservations))),
            assurance_required=assurance_required,
            assurance_satisfied=assurance_satisfied,
        )
        self.ledger.append(record_type="READINESS", record_id=result.readiness_id, object_ref=object_ref, record=result)
        return result

    def record_founder_decision(self, record: FounderDecision, *, actor_role: str) -> None:
        if actor_role != "FOUNDER":
            raise PermissionError("founder_decision_requires_explicit_founder_actor")
        readiness = self.ledger.records(object_ref=record.object_ref, record_type="READINESS")
        if not readiness:
            raise ValueError("founder_decision_requires_readiness_record")
        self.ledger.append(record_type="FOUNDER_DECISION", record_id=record.decision_id, object_ref=record.object_ref, record=record)
