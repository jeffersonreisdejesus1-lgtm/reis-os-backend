from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SnapshotClass(StrEnum):
    STATIC_PROFILE_DECLARATION = "static_profile_declaration"


class EvidenceState(StrEnum):
    DECLARED = "declared"
    OBSERVED = "observed"
    VERIFIED = "verified"
    ASSURED = "assured"


class NamespaceSemantics(StrEnum):
    DISTINCT_DECLARATIONS = "distinct_declarations"


class SourceMetadata(BaseModel):
    content_source_ref: str
    profile_version: str
    snapshot_class: SnapshotClass
    evidence_state: EvidenceState
    kernel_interface_ref: str


class NamespaceDeclarations(BaseModel):
    state: str
    memory: str
    semantics: NamespaceSemantics


class OCSProfileResponse(BaseModel):
    slug: str
    ocs_id: str
    identity: str
    specialty: str
    support_capabilities: list[str]
    allowed_action_classes: list[str]
    denied_action_classes: list[str]
    authority_envelope_ref: str
    namespaces: NamespaceDeclarations
    handoff_policy: str
    recovery_policy: str
    source: SourceMetadata


class OCSListResponse(BaseModel):
    items: list[OCSProfileResponse]
    count: int = Field(ge=0)
    source: SourceMetadata
