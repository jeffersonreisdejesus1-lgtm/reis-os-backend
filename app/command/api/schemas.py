from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.command.domain.assurance import (
    AssuranceStatus,
    AssuranceVerdict,
    HomologationState,
)
from app.command.domain.attention import AttentionClass, AttentionSeverity
from app.command.domain.observation import (
    FreshnessState,
    ObservationStatus,
    SourceType,
)


class CommandModeResponse(BaseModel):
    product: str = "REIS OS Command"
    milestone: str = "COMMAND v0.1 — OBSERVAR"
    mode: str = "observational_control_plane"
    private_enforcement: str = "requirement_not_yet_fully_validated"
    source_mutation_authority: str = "none"
    external_source_mutation: bool = False
    institutional_mutation: bool = False
    proposal_creation: bool = False
    external_action_invocation: bool = False
    enforcement: tuple[str, ...] = (
        "allowlist_only",
        "default_deny",
        "fail_closed",
    )


class ProjectionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    object_key: str
    object_type: str
    projection_type: str
    built_at: datetime
    freshness_state: FreshnessState
    reliability_status: ObservationStatus
    trusted_current: bool
    projection_payload: dict[str, object]


class AttentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    object_key: str
    attention_class: AttentionClass
    severity: AttentionSeverity
    reason: str
    explanation: str
    freshness_state: FreshnessState


class ProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: SourceType
    source_name: str
    source_reference: str
    source_revision: str | None
    observed_at: datetime
    source_updated_at: datetime | None
    retrieved_at: datetime
    observation_status: ObservationStatus
    freshness_state: FreshnessState
    current_confirmed: bool


class AssuranceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assurance_id: UUID
    object_key: str
    scope: str
    status: AssuranceStatus
    material: bool
    verdict: AssuranceVerdict | None
    evidence_refs: tuple[str, ...]
    performer_ref: str
    completed_at: datetime | None
    source_reference: str | None
    source_revision: str | None
    homologation_state: HomologationState


class ObjectDetailResponse(BaseModel):
    object_key: str
    object_type: str
    projection: ProjectionSummaryResponse | None
    provenance: tuple[ProvenanceResponse, ...]


class ConversationQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    object_keys: tuple[str, ...] = Field(default=(), max_length=20)
    limit: int = Field(default=20, ge=1, le=100)


class ConversationContextResponse(BaseModel):
    query_text: str
    mode: str
    conclusion: str
    situation: tuple[ProjectionSummaryResponse, ...]
    attention: tuple[AttentionResponse, ...]
    blockers: tuple[AttentionResponse, ...]
    decisions: tuple[AttentionResponse, ...]
    assurances: tuple[AssuranceResponse, ...]
    objects: tuple[ObjectDetailResponse, ...]
    evidence: tuple[ProvenanceResponse, ...]
    execution_available: bool = False
    assurance_execution_available: bool = False
    homologation_available: bool = False
    authority_granted: bool = False
