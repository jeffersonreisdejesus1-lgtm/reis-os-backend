from __future__ import annotations

from .contracts import (
    AssuranceRecord,
    CapabilityRecord,
    EvidenceCompleteness,
    EvidenceFreshness,
    EvidenceRef,
    FounderDecision,
    FounderDecisionValue,
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

    def _require_evidence_refs(self, *, object_ref: str, evidence_ids: tuple[str, ...], error: str) -> None:
        known = {
            r["record_id"]
            for r in self.ledger.records(object_ref=object_ref, record_type="EVIDENCE")
        }
        if not evidence_ids or any(evidence_id not in known for evidence_id in evidence_ids):
            raise ValueError(error)

    def add_quality_assessment(self, record: QualityAssessment) -> None:
        if record.applicable and record.verdict in {
            QualityVerdict.PASS,
            QualityVerdict.PASS_WITH_RESERVATIONS,
        }:
            self._require_evidence_refs(
                object_ref=record.object_ref,
                evidence_ids=record.evidence_ids,
                error="quality_pass_requires_existing_evidence",
            )
        self.ledger.append(record_type="QUALITY", record_id=record.assessment_id, object_ref=record.object_ref, record=record)

    def add_assurance(self, record: AssuranceRecord) -> None:
        if record.verdict.value.startswith("PASS"):
            self._require_evidence_refs(
                object_ref=record.object_ref,
                evidence_ids=record.evidence_ids,
                error="assurance_pass_requires_existing_evidence",
            )
        self.ledger.append(record_type="ASSURANCE", record_id=record.assurance_id, object_ref=record.object_ref, record=record)

    def add_metric(self, record: MetricObservation) -> None:
        if record.source_ref is None and record.completeness is not EvidenceCompleteness.UNKNOWN:
            raise ValueError("metric_without_source_must_be_unknown")
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
        latest = readiness[-1]["payload"]
        if record.decision in {
            FounderDecisionValue.APPROVE_FOR_RELEASE,
            FounderDecisionValue.APPROVE_WITH_EXPLICIT_RESERVATIONS,
        } and latest["status"] != ReadinessStatus.READY_FOR_FOUNDER_REVIEW.value:
            raise ValueError("founder_approval_requires_ready_for_review")
        self.ledger.append(record_type="FOUNDER_DECISION", record_id=record.decision_id, object_ref=record.object_ref, record=record)
