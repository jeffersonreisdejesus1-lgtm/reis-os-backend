from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.command.domain.attention import AttentionClass, AttentionSeverity
from app.command.domain.observation import FreshnessState, SourceType


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
    freshness_state: FreshnessState


class ObjectDetailResponse(BaseModel):
    object_key: str
    object_type: str
    projection: ProjectionSummaryResponse | None
    provenance: tuple[ProvenanceResponse, ...]
