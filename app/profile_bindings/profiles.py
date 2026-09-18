from __future__ import annotations

import unicodedata
from dataclasses import dataclass

KERNEL_INTERFACE_REF = "R1-UNIVERSAL-KERNEL@06393743bfc49ba2aa837a0a6e58c6b89bbe1704"
PROFILE_VERSION = "r2-v0.1.0"

OWNED_SYSTEM_CAPABILITY_ADAPTERS = frozenset(
    {
        "github.authenticated_connector",
        "codemagic.authenticated_connector",
        "reis_os.owned_runtime",
    }
)
OWNED_SYSTEM_TOOL_PERMISSIONS = frozenset(
    {
        "owned_system.read",
        "owned_system.build_trigger",
        "owned_system.bounded_write",
        "owned_system.bounded_configuration",
    }
)
OWNED_SYSTEM_DIRECT_ACCESS_OCS = frozenset({"SOFIA"})
OWNED_SYSTEM_ACCESS_CLASS = "owned_system_access_with_bound_authority"


@dataclass(frozen=True)
class OCSProfile:
    ocs_id: str
    identity: str
    ancestry: str
    constitution_ref: str
    csp_ref: str
    specialty: str
    support_capabilities: tuple[str, ...]
    authority_envelope_ref: str
    allowed_action_classes: tuple[str, ...]
    denied_action_classes: tuple[str, ...]
    evidence_profile: str
    pi_activation_policy: str
    capability_adapters: tuple[str, ...]
    tool_permissions: tuple[str, ...]
    state_namespace: str
    memory_namespace: str
    risk_model: str
    stop_policy: str
    handoff_policy: str
    recovery_policy: str
    version: str
    predecessor: str
    rollback_pointer: str
    kernel_interface_ref: str = KERNEL_INTERFACE_REF


def _slugify_ocs_id(ocs_id: str) -> str:
    normalized = unicodedata.normalize("NFKD", ocs_id)
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def _profile(
    ocs_id: str,
    specialty: str,
    allowed: tuple[str, ...],
    denied: tuple[str, ...],
    support: tuple[str, ...],
    capability_adapters: tuple[str, ...] = (),
    tool_permissions: tuple[str, ...] = (),
) -> OCSProfile:
    slug = _slugify_ocs_id(ocs_id)
    return OCSProfile(
        ocs_id=ocs_id,
        identity=f"identity://{slug}",
        ancestry=f"ancestry://{slug}",
        constitution_ref=f"constitution://{slug}/current",
        csp_ref=f"csp://{slug}/current",
        specialty=specialty,
        support_capabilities=support,
        authority_envelope_ref=f"authority://{slug}/current",
        allowed_action_classes=allowed,
        denied_action_classes=denied,
        evidence_profile=f"evidence://{slug}/risk-dependent",
        pi_activation_policy=f"pi://{slug}/local-only",
        capability_adapters=capability_adapters,
        tool_permissions=tool_permissions,
        state_namespace=f"state://{slug}/{PROFILE_VERSION}",
        memory_namespace=f"memory://{slug}/{PROFILE_VERSION}",
        risk_model=f"risk://{slug}/csp-bound",
        stop_policy="deny_hold_escalate_on_invalid_scope_authority_lease_or_evidence",
        handoff_policy="context_and_evidence_refs_only;authority_transfer=false;memory_import=false",
        recovery_policy=f"recovery://{slug}/verified-checkpoint-only",
        version=PROFILE_VERSION,
        predecessor=KERNEL_INTERFACE_REF,
        rollback_pointer=KERNEL_INTERFACE_REF,
    )


PROFILES: dict[str, OCSProfile] = {
    "NÓESIS": _profile(
        "NÓESIS",
        "orchestration_governance_routing_program_coordination_state",
        ("orchestrate", "route", "govern_epistemic_state", "govern_program_state"),
        ("direct_material_implementation", "self_assurance", "authority_creation"),
        ("coordination", "routing", "governance"),
    ),
    "DÉDALA": _profile(
        "DÉDALA",
        "technical_architecture_systems_integration_security_recovery",
        ("architectural_analysis", "technical_design", "technical_recovery_planning"),
        ("unmediated_material_effect", "self_assurance", "nontechnical_domain_takeover"),
        ("architecture", "systems", "security", "integration"),
    ),
    "SÝNESIS": _profile(
        "SÝNESIS",
        "independent_institutional_assurance",
        ("independent_verification", "falsification", "assurance_judgment"),
        ("primary_construction_under_assurance", "self_assurance", "promotion"),
        ("assurance", "verification", "falsification"),
    ),
    "ÍRIS": _profile(
        "ÍRIS",
        "ux_ui_interaction_perception_accessibility",
        ("experience_analysis", "design_artifact", "accessibility_analysis"),
        ("architecture_security_takeover", "self_assurance", "authority_expansion"),
        ("ux", "ui", "accessibility"),
    ),
    "LYRA": _profile(
        "LYRA",
        "branding_identity_positioning_language_brand_communication",
        ("brand_artifact", "identity_artifact", "positioning_artifact"),
        ("implementation_authority_by_profile", "cross_domain_takeover"),
        ("brand", "identity", "positioning", "communication"),
    ),
    "SOFIA": _profile(
        "SOFIA",
        "software_implementation_code_incremental_integration",
        (
            "software_implementation_via_valid_envelope_lease_effector",
            OWNED_SYSTEM_ACCESS_CLASS,
        ),
        ("architecture_rewrite_without_authority", "self_assurance", "lateral_effect_route"),
        ("code", "integration", "implementation"),
        capability_adapters=(
            "github.authenticated_connector",
            "codemagic.authenticated_connector",
            "reis_os.owned_runtime",
        ),
        tool_permissions=(
            "owned_system.read",
            "owned_system.build_trigger",
            "owned_system.bounded_write",
            "owned_system.bounded_configuration",
        ),
    ),
    "MÊTIS": _profile(
        "MÊTIS",
        "research_intelligence_strategy_market_hypotheses",
        ("research", "strategic_analysis", "falsifiable_recommendation"),
        ("material_execution_by_inference", "administrative_system_of_record_takeover"),
        ("research", "strategy", "market_intelligence"),
    ),
    "ÁGORA": _profile(
        "ÁGORA",
        "technical_qa_software_audit_reproducibility_implementation_conformance",
        ("independent_technical_verification",),
        ("primary_implementation_under_verification", "self_assurance", "promotion"),
        ("qa", "audit", "reproducibility", "conformance"),
    ),
    "AURI": _profile(
        "AURI",
        "administration_priority_continuity_system_of_record",
        ("administrative_coordination", "record_write_with_explicit_authority"),
        ("technical_strategic_authority_by_profile", "unconfirmed_write"),
        ("administration", "records", "continuity"),
    ),
    "SYNERGEIA": _profile(
        "SYNERGEIA",
        "gtm_activation_distribution_channels_market_coordination",
        ("gtm_execution_with_approved_strategy_budget_authority", "channel_coordination"),
        ("strategy_invention_as_authority", "unapproved_spend", "unapproved_publication"),
        ("gtm", "activation", "distribution", "channels"),
    ),
    "TÊMIS": _profile(
        "TÊMIS",
        "android_google_play_stewardship",
        ("android_policy_analysis", "play_store_readiness_assessment", "android_architecture_review"),
        ("production_publication", "self_assurance", "authority_creation", "unapproved_commerce_change"),
        ("android", "google_play", "policy", "store_readiness"),
    ),
}


def get_profile(ocs_id: str) -> OCSProfile:
    return PROFILES[ocs_id]


def validate_profiles(profiles: dict[str, OCSProfile] = PROFILES) -> None:
    if len(profiles) != 11:
        raise ValueError("eleven_distinct_ocs_profiles_required")
    if len({profile.identity for profile in profiles.values()}) != 11:
        raise ValueError("profile_identity_merge_prohibited")
    if len({profile.state_namespace for profile in profiles.values()}) != 11:
        raise ValueError("state_namespace_isolation_required")
    if len({profile.memory_namespace for profile in profiles.values()}) != 11:
        raise ValueError("memory_namespace_isolation_required")
    for profile in profiles.values():
        if not profile.authority_envelope_ref:
            raise ValueError("explicit_authority_reference_required")
        if profile.kernel_interface_ref != KERNEL_INTERFACE_REF:
            raise ValueError("kernel_interface_mismatch")
        if "authority_transfer=false" not in profile.handoff_policy:
            raise ValueError("handoff_authority_transfer_prohibited")
        if "memory_import=false" not in profile.handoff_policy:
            raise ValueError("cross_ocs_memory_import_prohibited")

        has_direct_route = bool(profile.capability_adapters or profile.tool_permissions)
        if not has_direct_route:
            continue

        if profile.ocs_id not in OWNED_SYSTEM_DIRECT_ACCESS_OCS:
            raise ValueError("direct_effect_route_prohibited")
        if OWNED_SYSTEM_ACCESS_CLASS not in profile.allowed_action_classes:
            raise ValueError("owned_system_access_class_required")
        if not profile.capability_adapters or not profile.tool_permissions:
            raise ValueError("owned_system_route_requires_adapter_and_permissions")
        if not set(profile.capability_adapters).issubset(OWNED_SYSTEM_CAPABILITY_ADAPTERS):
            raise ValueError("unapproved_owned_system_adapter")
        if not set(profile.tool_permissions).issubset(OWNED_SYSTEM_TOOL_PERMISSIONS):
            raise ValueError("unapproved_owned_system_tool_permission")
