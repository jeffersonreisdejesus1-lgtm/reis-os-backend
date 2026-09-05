from __future__ import annotations

from app.command.api.schemas import (
    EvidenceState,
    NamespaceDeclarations,
    NamespaceSemantics,
    OCSListResponse,
    OCSProfileResponse,
    SnapshotClass,
    SourceMetadata,
)
from app.profile_bindings.profiles import (
    KERNEL_INTERFACE_REF,
    PROFILE_VERSION,
    PROFILES,
    OCSProfile,
    validate_profiles,
)

CONTENT_SOURCE_REF = (
    "repo://jeffersonreisdejesus1-lgtm/reis-os-backend/"
    "app/profile_bindings/profiles.py"
)

OCS_SLUGS: dict[str, str] = {
    "NÓESIS": "noesis",
    "DÉDALA": "dedala",
    "SÝNESIS": "synesis",
    "ÍRIS": "iris",
    "LYRA": "lyra",
    "SOFIA": "sofia",
    "MÊTIS": "metis",
    "ÁGORA": "agora",
    "AURI": "auri",
    "SYNERGEIA": "synergeia",
}
SLUG_TO_OCS_ID = {slug: ocs_id for ocs_id, slug in OCS_SLUGS.items()}


def _source() -> SourceMetadata:
    return SourceMetadata(
        content_source_ref=CONTENT_SOURCE_REF,
        profile_version=PROFILE_VERSION,
        snapshot_class=SnapshotClass.STATIC_PROFILE_DECLARATION,
        evidence_state=EvidenceState.DECLARED,
        kernel_interface_ref=KERNEL_INTERFACE_REF,
    )


def project_profile(profile: OCSProfile) -> OCSProfileResponse:
    return OCSProfileResponse(
        slug=OCS_SLUGS[profile.ocs_id],
        ocs_id=profile.ocs_id,
        identity=profile.identity,
        specialty=profile.specialty,
        support_capabilities=list(profile.support_capabilities),
        allowed_action_classes=list(profile.allowed_action_classes),
        denied_action_classes=list(profile.denied_action_classes),
        authority_envelope_ref=profile.authority_envelope_ref,
        namespaces=NamespaceDeclarations(
            state=profile.state_namespace,
            memory=profile.memory_namespace,
            semantics=NamespaceSemantics.DISTINCT_DECLARATIONS,
        ),
        handoff_policy=profile.handoff_policy,
        recovery_policy=profile.recovery_policy,
        source=_source(),
    )


def _validate_serving_contract() -> None:
    validate_profiles(PROFILES)
    if set(OCS_SLUGS) != set(PROFILES):
        raise ValueError("command_profile_slug_coverage_required")
    if len(SLUG_TO_OCS_ID) != len(PROFILES):
        raise ValueError("command_profile_slugs_must_be_unique")
    if any(not slug.isascii() or not slug.isalpha() for slug in SLUG_TO_OCS_ID):
        raise ValueError("command_profile_slugs_must_be_ascii_alpha")


def list_ocs_profiles() -> OCSListResponse:
    _validate_serving_contract()
    items = [
        project_profile(PROFILES[ocs_id])
        for ocs_id in OCS_SLUGS
    ]
    return OCSListResponse(items=items, count=len(items), source=_source())


def get_ocs_profile(ocs_slug: str) -> OCSProfileResponse | None:
    _validate_serving_contract()
    ocs_id = SLUG_TO_OCS_ID.get(ocs_slug.casefold())
    return None if ocs_id is None else project_profile(PROFILES[ocs_id])
