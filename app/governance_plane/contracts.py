from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class EvidenceFreshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class QualityVerdict(StrEnum):
    PASS = "PASS"
    PASS_WITH_RESERVATIONS = "PASS_WITH_RESERVATIONS"
    HOLD = "HOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class AssuranceVerdict(StrEnum):
    PASS = "PASS"
    PASS_WITH_RESERVATIONS = "PASS_WITH_RESERVATIONS"
    HOLD = "HOLD"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNKNOWN = "UNKNOWN"


class ReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    READY_FOR_FOUNDER_REVIEW = "READY_FOR_FOUNDER_REVIEW"


class FounderDecisionValue(StrEnum):
    APPROVE_FOR_RELEASE = "APPROVE_FOR_RELEASE"
    APPROVE_WITH_EXPLICIT_RESERVATIONS = "APPROVE_WITH_EXPLICIT_RESERVATIONS"
    RETURN_FOR_REFACTOR = "RETURN_FOR_REFACTOR"
    HOLD = "HOLD"
    REJECT_BASELINE = "REJECT_BASELINE"


class CapabilityKind(StrEnum):
    CONNECTOR = "CONNECTOR"
    MCP = "MCP"
    HOST_ADAPTER = "HOST_ADAPTER"
    PROVIDER_ENDPOINT = "PROVIDER_ENDPOINT"
    FEDERATED_SEAT = "FEDERATED_SEAT"


class CapabilityHealth(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    object_ref: str
    source_ref: str
    source_hash: str
    observed_at: str
    completeness: EvidenceCompleteness
    freshness: EvidenceFreshness


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    assessment_id: str
    object_ref: str
    domain: str
    applicable: bool
    verdict: QualityVerdict
    assessor_ref: str
    evidence_ids: tuple[str, ...]
    reservations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssuranceRecord:
    assurance_id: str
    object_ref: str
    assurer_ref: str
    verdict: AssuranceVerdict
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PromotionReadiness:
    readiness_id: str
    object_ref: str
    status: ReadinessStatus
    evidence_complete: bool
    open_blockers: tuple[str, ...]
    reservations: tuple[str, ...]
    assurance_required: bool
    assurance_satisfied: bool


@dataclass(frozen=True, slots=True)
class FounderDecision:
    decision_id: str
    object_ref: str
    decision: FounderDecisionValue
    founder_actor_ref: str
    decided_at: str
    reservations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MetricObservation:
    metric_id: str
    object_ref: str
    metric_name: str
    value: float | int | None
    source_ref: str | None
    measurement_method: str
    measurement_version: str
    observed_at: str
    window: str
    completeness: EvidenceCompleteness


@dataclass(frozen=True, slots=True)
class RefactorEvent:
    refactor_id: str
    object_ref: str
    refactor_class: str
    reason: str
    started_at: str
    ended_at: str | None
    affected_contracts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    capability_id: str
    provider: str
    kind: CapabilityKind
    seat: str | None
    integration_ref: str | None
    can_read: bool
    can_write: bool
    can_model_invoke: bool
    connection_validated: bool
    machine_receipt_supported: bool
    source_of_truth_role: str | None
    health: CapabilityHealth
    observed_at: str
    capability_version: str
