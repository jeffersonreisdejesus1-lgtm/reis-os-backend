from __future__ import annotations

from app.command.api.schemas import (
    EvidenceState,
    FreshnessClass,
    OCSListResponse,
    OCSProfileResponse,
    SourceMetadata,
)
from app.profile_bindings.profiles import (
    KERNEL_INTERFACE_REF,
    PROFILE_VERSION,
    PROFILES,
    OCSProfile,
)


def _source() -> SourceMetadata:
    return SourceMetadata(
        source_ref=KERNEL_INTERFACE_REF,
        profile_version=PROFILE_VERSION,
        freshness=FreshnessClass.STATIC_VERSIONED,
        evidence_state=EvidenceState.OBSERVED,
    )


def project_profile(profile: OCSProfile) -> OCSProfileResponse:
    return OCSProfileResponse(
        ocs_id=profile.ocs_id,
        identity=profile.identity,
        specialty=profile.specialty,
        support_capabilities=list(profile.support_capabilities),
        allowed_action_classes=list(profile.allowed_action_classes),
        denied_action_classes=list(profile.denied_action_classes),
        authority_envelope_ref=profile.authority_envelope_ref,
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        handoff_policy=profile.handoff_policy,
        recovery_policy=profile.recovery_policy,
        source=_source(),
    )


def list_ocs_profiles() -> OCSListResponse:
    items = [project_profile(PROFILES[key]) for key in sorted(PROFILES)]
    return OCSListResponse(items=items, count=len(items), source=_source())


def get_ocs_profile(ocs_id: str) -> OCSProfileResponse | None:
    profile = PROFILES.get(ocs_id.upper())
    return None if profile is None else project_profile(profile)
