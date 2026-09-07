from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

SCHEMA_VERSION = "governance-candidate-v0.1"


class Completeness(StrEnum):
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


class GateVerdict(StrEnum):
    UNKNOWN = "UNKNOWN"
    OPEN = "OPEN"
    PASS_WITH_RESERVATIONS = "PASS_WITH_RESERVATIONS"
    FAIL = "FAIL"
    HOLD = "HOLD"


class QualityVerdict(StrEnum):
    UNKNOWN = "UNKNOWN"
    SATISFIED = "SATISFIED"
    SATISFIED_WITH_RESERVATIONS = "SATISFIED_WITH_RESERVATIONS"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Readiness(StrEnum):
    NOT_READY = "NOT_READY"
    READY_FOR_FOUNDER_REVIEW = "READY_FOR_FOUNDER_REVIEW"


class FounderDecision(StrEnum):
    APPROVE_FOR_RELEASE = "APPROVE_FOR_RELEASE"
    APPROVE_WITH_EXPLICIT_RESERVATIONS = "APPROVE_WITH_EXPLICIT_RESERVATIONS"
    RETURN_FOR_REFACTOR = "RETURN_FOR_REFACTOR"
    HOLD = "HOLD"
    REJECT_BASELINE = "REJECT_BASELINE"


class RefactorClass(StrEnum):
    DEFECT_CORRECTION = "DEFECT_CORRECTION"
    QUALITY_REFACTOR = "QUALITY_REFACTOR"
    ARCHITECTURAL_REFACTOR = "ARCHITECTURAL_REFACTOR"
    PRODUCT_REFINEMENT = "PRODUCT_REFINEMENT"


class AvailabilityState(StrEnum):
    UNKNOWN = "UNKNOWN"
    NATIVE_HOST_ONLY = "NATIVE_HOST_ONLY"
    OPERATIONALLY_BOUND = "OPERATIONALLY_BOUND"
    RECOVERABLE = "RECOVERABLE"
    UNAVAILABLE = "UNAVAILABLE"


class RoutingState(StrEnum):
    UNKNOWN = "UNKNOWN"
    ADDRESSABLE = "ADDRESSABLE"
    HOLD = "HOLD"


class CapabilityClass(StrEnum):
    CONNECTOR = "CONNECTOR"
    MCP = "MCP"
    HOST_ADAPTER = "HOST_ADAPTER"
    PROVIDER_ENDPOINT = "PROVIDER_ENDPOINT"
    FEDERATED_SEAT = "FEDERATED_SEAT"


@dataclass(frozen=True, slots=True)
class SourceLink:
    source_type: str
    source_ref: str
    relation: str

    def __post_init__(self) -> None:
        _required(self.source_type, self.source_ref, self.relation)


type Refs = tuple[str, ...]
type SourceLinks = tuple[SourceLink, ...]


@dataclass(frozen=True, slots=True)
class MissionMetricsRecord:
    record_id: str
    mission_id: str
    ocs_id: str
    product_id: str | None
    gate_id: str | None
    started_at: datetime
    completed_at: datetime | None
    active_execution_seconds: int | None
    waiting_seconds: int | None
    founder_wait_seconds: int | None
    external_wait_seconds: int | None
    retries: int | None
    failures: int | None
    refactors: int | None
    founder_interventions: int | None
    autonomous_completion: bool | None
    source_refs: Refs
    source_links: SourceLinks
    provenance_refs: Refs
    measurement_method: str
    measurement_version: str
    observed_at: datetime
    completeness: Completeness
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.record_id,
            self.mission_id,
            self.ocs_id,
            self.measurement_method,
            self.measurement_version,
        )
        _non_negative_optional(
            self.active_execution_seconds,
            self.waiting_seconds,
            self.founder_wait_seconds,
            self.external_wait_seconds,
            self.retries,
            self.failures,
            self.refactors,
            self.founder_interventions,
        )
        _aware(self.started_at, self.completed_at, self.observed_at)

    def effective_completeness(self, now: datetime) -> Completeness:
        _aware(now)
        if self.observed_at > now:
            return Completeness.UNKNOWN
        return self.completeness

    def promotable_measurement(self, now: datetime) -> bool:
        known = self.effective_completeness(now) is not Completeness.UNKNOWN
        return bool(self.source_refs) and known


@dataclass(frozen=True, slots=True)
class GatePerformanceRecord:
    gate_id: str
    object_ref: str
    gate_class: str
    opened_at: datetime
    closed_at: datetime | None
    elapsed_seconds: int | None
    blocking_seconds: int | None
    owner_ocs: str
    verifier_ocs: str | None
    assurance_required: bool
    evidence_refs: Refs
    source_links: SourceLinks
    provenance_refs: Refs
    blockers: Refs
    findings: Refs
    verdict: GateVerdict
    routing_result: str | None
    version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.gate_id,
            self.object_ref,
            self.gate_class,
            self.owner_ocs,
            self.version,
        )
        _aware(self.opened_at, self.closed_at)
        _non_negative_optional(self.elapsed_seconds, self.blocking_seconds)


@dataclass(frozen=True, slots=True)
class QualityApplicabilityMatrix:
    matrix_id: str
    object_ref: str
    domain: str
    applicable: bool
    reason: str
    required_evidence: Refs
    mandatory_for_promotion: bool
    source_links: SourceLinks
    provenance_refs: Refs
    version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.matrix_id,
            self.object_ref,
            self.domain,
            self.reason,
            self.version,
        )


@dataclass(frozen=True, slots=True)
class QualityDomainAssessment:
    assessment_id: str
    product_id: str
    baseline_ref: str
    domain: str
    applicable: bool
    applicability_reason: str
    assessor_ocs: str
    evidence_refs: Refs
    source_links: SourceLinks
    provenance_refs: Refs
    findings: Refs
    verdict: QualityVerdict
    assessed_at: datetime
    assessment_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.assessment_id,
            self.product_id,
            self.baseline_ref,
            self.domain,
            self.applicability_reason,
            self.assessor_ocs,
            self.assessment_version,
        )
        _aware(self.assessed_at)
        if not self.applicable and self.verdict is not QualityVerdict.NOT_APPLICABLE:
            raise ValueError("non_applicable_domain_requires_not_applicable_verdict")


@dataclass(frozen=True, slots=True)
class QualityEvidenceBundle:
    bundle_id: str
    baseline_ref: str
    evidence_refs: Refs
    provenance_refs: Refs
    source_links: SourceLinks
    assessment_refs: Refs
    assurance_refs: Refs
    known_limitations: Refs
    evidence_completeness: Completeness
    created_at: datetime
    bundle_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(self.bundle_id, self.baseline_ref, self.bundle_version)
        _aware(self.created_at)


@dataclass(frozen=True, slots=True)
class PromotionReadinessState:
    readiness_id: str
    product_id: str
    baseline_ref: str
    required_domains: Refs
    completed_assessments: Refs
    open_blockers: Refs
    assurance_state: str
    readiness: Readiness
    evidence_bundle_ref: str
    derived_from: Refs
    source_links: SourceLinks
    provenance_refs: Refs
    derivation_version: str
    derived_at: datetime
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.readiness_id,
            self.product_id,
            self.baseline_ref,
            self.assurance_state,
            self.evidence_bundle_ref,
            self.derivation_version,
        )
        _aware(self.derived_at)

    @property
    def releases_product(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class FounderApprovalDecision:
    decision_id: str
    product_id: str
    baseline_ref: str
    evidence_bundle_ref: str
    decision: FounderDecision
    reservations: Refs
    authority_ref: str
    decided_at: datetime
    explicit_founder_act_ref: str
    source_links: SourceLinks
    provenance_refs: Refs
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.decision_id,
            self.product_id,
            self.baseline_ref,
            self.evidence_bundle_ref,
            self.authority_ref,
            self.explicit_founder_act_ref,
        )
        _aware(self.decided_at)


@dataclass(frozen=True, slots=True)
class RefactorEvent:
    refactor_id: str
    object_ref: str
    refactor_class: RefactorClass
    reason: str
    discovered_at_stage: str
    affected_contracts: Refs
    started_at: datetime
    completed_at: datetime | None
    elapsed_seconds: int | None
    recurrence_ref: str | None
    evidence_refs: Refs
    source_links: SourceLinks
    provenance_refs: Refs
    learning_ref: str | None
    event_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.refactor_id,
            self.object_ref,
            self.reason,
            self.discovered_at_stage,
            self.event_version,
        )
        _aware(self.started_at, self.completed_at)
        _non_negative_optional(self.elapsed_seconds)


@dataclass(frozen=True, slots=True)
class IntegrationCapabilityRecord:
    integration_id: str
    provider: str
    category: str
    purpose: str
    connection_status: str
    validation_status: str
    read_capabilities: Refs
    write_capabilities: Refs
    supported_artifacts: Refs
    authentication_boundary: str
    canonical_source_role: str | None
    primary_ocs_users: Refs
    authorized_use_cases: Refs
    prohibited_use_cases: Refs
    known_limitations: Refs
    security_risks: Refs
    data_risks: Refs
    reversibility: str
    evidence_capability: str
    last_validated_at: datetime | None
    capability_version: str
    source_links: SourceLinks
    provenance_refs: Refs
    capability_class: CapabilityClass = CapabilityClass.CONNECTOR
    seat_ref: str | None = None
    host_ref: str | None = None
    model_invoke_capabilities: Refs = ()
    source_access_status: str = "UNKNOWN"
    live_model_invocation_status: str = "UNKNOWN"
    host_adapter_available: bool = False
    machine_verifiable_receipt: bool = False
    source_access_validated: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.integration_id,
            self.provider,
            self.category,
            self.purpose,
            self.connection_status,
            self.validation_status,
            self.authentication_boundary,
            self.reversibility,
            self.evidence_capability,
            self.capability_version,
        )
        _aware(self.last_validated_at)
        if self.live_model_invocation_status == "AVAILABLE":
            if not self.host_adapter_available:
                raise ValueError("live_model_invocation_requires_host_adapter")
            if not self.model_invoke_capabilities:
                raise ValueError("live_model_invocation_requires_capability")
            if not self.machine_verifiable_receipt:
                raise ValueError("live_model_invocation_requires_machine_receipt")


@dataclass(frozen=True, slots=True)
class AgentAvailabilityContract:
    contract_id: str
    ocs_id: str
    availability_state: AvailabilityState
    current_instance_id: str | None
    generation: int | None
    mission_bound: bool
    lease_status: str
    recovery_ready: bool
    recovery_proof_ref: str | None
    auxiliary_spawn: bool
    chat_addressable: bool
    last_checkpoint_ref: str | None
    last_readback_ref: str | None
    evidence_state: Completeness
    freshness_at: datetime | None
    source_links: SourceLinks
    provenance_refs: Refs
    contract_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.contract_id,
            self.ocs_id,
            self.lease_status,
            self.contract_version,
        )
        _aware(self.freshness_at)
        _non_negative_optional(self.generation)
        recoverable = self.availability_state is AvailabilityState.RECOVERABLE
        if recoverable and not self.recovery_proof_ref:
            raise ValueError("recoverable_requires_proof_ref")


@dataclass(frozen=True, slots=True)
class ChatInstitutionalRoutingContract:
    route_id: str
    addressed_ocs_id: str
    mission_id: str
    resolved_instance_id: str | None
    generation: int | None
    routing_state: RoutingState
    route_receipt_ref: str | None
    response_correlation_id: str
    chat_addressable: bool
    chat_native_execution: bool
    source_links: SourceLinks
    provenance_refs: Refs
    contract_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.route_id,
            self.addressed_ocs_id,
            self.mission_id,
            self.response_correlation_id,
            self.contract_version,
        )
        _non_negative_optional(self.generation)
        if self.chat_native_execution:
            raise ValueError("chat_native_execution_unproven")


@dataclass(frozen=True, slots=True)
class AuxiliaryAgentEvidenceContract:
    evidence_id: str
    parent_ocs_id: str
    auxiliary_id: str
    mission_id: str
    requested_scope: Refs
    parent_authority_scope: Refs
    produced_evidence_refs: Refs
    created_new_ocs_identity: bool
    source_links: SourceLinks
    provenance_refs: Refs
    contract_version: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required(
            self.evidence_id,
            self.parent_ocs_id,
            self.auxiliary_id,
            self.mission_id,
            self.contract_version,
        )
        parent_scope = set(self.parent_authority_scope)
        if not set(self.requested_scope).issubset(parent_scope):
            raise ValueError("auxiliary_authority_escapes_parent")
        if self.created_new_ocs_identity:
            raise ValueError("auxiliary_cannot_create_ocs_identity")


type CandidateRecord = (
    MissionMetricsRecord
    | GatePerformanceRecord
    | QualityApplicabilityMatrix
    | QualityDomainAssessment
    | QualityEvidenceBundle
    | PromotionReadinessState
    | FounderApprovalDecision
    | RefactorEvent
    | IntegrationCapabilityRecord
    | AgentAvailabilityContract
    | ChatInstitutionalRoutingContract
    | AuxiliaryAgentEvidenceContract
)


def record_id(record: CandidateRecord) -> str:
    if isinstance(record, MissionMetricsRecord):
        return record.record_id
    if isinstance(record, GatePerformanceRecord):
        return record.gate_id
    if isinstance(record, QualityApplicabilityMatrix):
        return record.matrix_id
    if isinstance(record, QualityDomainAssessment):
        return record.assessment_id
    if isinstance(record, QualityEvidenceBundle):
        return record.bundle_id
    if isinstance(record, PromotionReadinessState):
        return record.readiness_id
    if isinstance(record, FounderApprovalDecision):
        return record.decision_id
    if isinstance(record, RefactorEvent):
        return record.refactor_id
    if isinstance(record, IntegrationCapabilityRecord):
        return record.integration_id
    if isinstance(record, AgentAvailabilityContract):
        return record.contract_id
    if isinstance(record, ChatInstitutionalRoutingContract):
        return record.route_id
    return record.evidence_id


def _required(*values: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError("required_candidate_field_missing")


def _non_negative_optional(*values: int | None) -> None:
    if any(value is not None and value < 0 for value in values):
        raise ValueError("negative_candidate_measurement")


def _aware(*values: datetime | None) -> None:
    for value in values:
        if value is not None and value.tzinfo is None:
            raise ValueError("timezone_aware_timestamp_required")
