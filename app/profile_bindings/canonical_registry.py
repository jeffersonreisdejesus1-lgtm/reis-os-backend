from __future__ import annotations

from app.profile_bindings.cupuwa_visual_profiles import CUPUWA_VISUAL_PROFILES
from app.profile_bindings.profiles import KERNEL_INTERFACE_REF, OCSProfile, PROFILES, _profile

REGISTRY_ID = "REIS-OS-OCS-CANONICAL-REGISTRY-001"
REGISTRY_VERSION = "v0.1.0"

# TÊMIS is the historically defined 11th OCS: Android / Google Play stewardship,
# including publication-policy, privacy/data, permissions/SDKs, Data Safety,
# content, purchases/ads, age-rating and Android/Play compliance review.
TEMIS = _profile(
    "TÊMIS",
    "android_google_play_stewardship_policy_privacy_publication_compliance",
    (
        "android_play_compliance_analysis",
        "play_publication_readiness_review",
        "privacy_data_safety_review",
        "android_policy_findings",
    ),
    (
        "primary_software_implementation",
        "self_assurance",
        "unmediated_publication",
        "credential_access_by_profile",
        "authority_creation",
        "automatic_promotion",
    ),
    (
        "android",
        "google_play",
        "play_policy",
        "privacy",
        "data_safety",
        "publication_compliance",
    ),
)

FOUNDATION_OCS: dict[str, OCSProfile] = dict(PROFILES)
ELEVENTH_OCS: dict[str, OCSProfile] = {"TÊMIS": TEMIS}
CUPUWA_SPECIALIST_OCS: dict[str, OCSProfile] = dict(CUPUWA_VISUAL_PROFILES)

CANONICAL_OCS_REGISTRY: dict[str, OCSProfile] = {
    **FOUNDATION_OCS,
    **ELEVENTH_OCS,
    **CUPUWA_SPECIALIST_OCS,
}

EXPECTED_OCS_IDS = {
    "NÓESIS", "DÉDALA", "SÝNESIS", "ÍRIS", "LYRA", "SOFIA", "MÊTIS", "ÁGORA",
    "AURI", "SYNERGEIA", "TÊMIS", "AURA", "EIKÓN", "TÝPOS", "GRAMMÉ", "LÉXIS",
    "CHRÔMA", "SÊMA", "KINÉSIS", "FIGMA", "DÉSMOS", "GÉPHYRA", "HÉSTIA", "ROTA",
    "PRÁXIS", "MORPHÉ", "ARGOS", "DOKIMÉ", "LEÍA", "KRITÉRION",
}


def get_canonical_profile(ocs_id: str) -> OCSProfile:
    return CANONICAL_OCS_REGISTRY[ocs_id]


def validate_canonical_registry() -> None:
    if set(CANONICAL_OCS_REGISTRY) != EXPECTED_OCS_IDS:
        missing = EXPECTED_OCS_IDS - set(CANONICAL_OCS_REGISTRY)
        extra = set(CANONICAL_OCS_REGISTRY) - EXPECTED_OCS_IDS
        raise ValueError(f"canonical_registry_mismatch:missing={sorted(missing)}:extra={sorted(extra)}")
    if len(CANONICAL_OCS_REGISTRY) != 30:
        raise ValueError("thirty_canonical_ocs_required")

    profiles = tuple(CANONICAL_OCS_REGISTRY.values())
    if len({p.identity for p in profiles}) != 30:
        raise ValueError("canonical_identity_isolation_required")
    if len({p.state_namespace for p in profiles}) != 30:
        raise ValueError("canonical_state_namespace_isolation_required")
    if len({p.memory_namespace for p in profiles}) != 30:
        raise ValueError("canonical_memory_namespace_isolation_required")
    if len({p.specialty for p in profiles}) != 30:
        raise ValueError("canonical_specialty_collision_prohibited")

    for profile in profiles:
        if profile.kernel_interface_ref != KERNEL_INTERFACE_REF:
            raise ValueError("kernel_interface_mismatch")
        if not profile.authority_envelope_ref:
            raise ValueError("explicit_authority_reference_required")
        if "authority_transfer=false" not in profile.handoff_policy:
            raise ValueError("handoff_authority_transfer_prohibited")
        if "memory_import=false" not in profile.handoff_policy:
            raise ValueError("cross_ocs_memory_import_prohibited")
        if profile.capability_adapters or profile.tool_permissions:
            raise ValueError("direct_effect_route_prohibited")

    if "unmediated_publication" not in TEMIS.denied_action_classes:
        raise ValueError("temis_direct_publication_prohibited")
    if "credential_access_by_profile" not in TEMIS.denied_action_classes:
        raise ValueError("temis_direct_credential_route_prohibited")
