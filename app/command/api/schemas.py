from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FreshnessClass(StrEnum):
    STATIC_VERSIONED = "static_versioned"
    LIVE_STREAM = "live_stream"
    NEAR_REAL_TIME = "near_real_time"
    LAST_KNOWN_STATE = "last_known_state"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class EvidenceState(StrEnum):
    DECLARED = "declared"
    OBSERVED = "observed"
    VERIFIED = "verified"
    ASSURED = "assured"


class SourceMetadata(BaseModel):
    source_ref: str
    profile_version: str
    freshness: FreshnessClass
    evidence_state: EvidenceState


class OCSProfileResponse(BaseModel):
    ocs_id: str
    identity: str
    specialty: str
    support_capabilities: list[str]
    allowed_action_classes: list[str]
    denied_action_classes: list[str]
    authority_envelope_ref: str
    state_namespace: str
    memory_namespace: str
    handoff_policy: str
    recovery_policy: str
    source: SourceMetadata


class OCSListResponse(BaseModel):
    items: list[OCSProfileResponse]
    count: int = Field(ge=0)
    source: SourceMetadata
