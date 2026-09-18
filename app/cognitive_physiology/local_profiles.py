from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalCognitiveProfile:
    ocs_name: str
    identity_ref: str
    institutional_id: str
    specialty: str
    state_namespace: str
    memory_namespace: str
    reference_role: str


LOCAL_PROFILES: dict[str, LocalCognitiveProfile] = {
    "NÓESIS": LocalCognitiveProfile(
        "NÓESIS", "identity://noesis", "identity://noesis",
        "orchestration_governance_routing_program_coordination_state",
        "state://noesis/r2-v0.1.0", "memory://noesis/r2-v0.1.0",
        "reference_pilot_only",
    ),
    "DÉDALA": LocalCognitiveProfile(
        "DÉDALA", "identity://dedala", "identity://dedala",
        "technical_architecture_systems_integration_security_recovery",
        "state://dedala/r2-v0.1.0", "memory://dedala/r2-v0.1.0",
        "governance_evidence_stress",
    ),
    "SÝNESIS": LocalCognitiveProfile(
        "SÝNESIS", "identity://synesis", "identity://synesis",
        "independent_institutional_assurance",
        "state://synesis/r2-v0.1.0", "memory://synesis/r2-v0.1.0",
        "governance_evidence_stress_self_assurance_forbidden",
    ),
    "ÍRIS": LocalCognitiveProfile(
        "ÍRIS", "identity://iris", "identity://iris",
        "ux_ui_interaction_perception_accessibility",
        "state://iris/r2-v0.1.0", "memory://iris/r2-v0.1.0",
        "semantic_human_interface_stress",
    ),
    "LYRA": LocalCognitiveProfile(
        "LYRA", "identity://lyra", "identity://lyra",
        "branding_identity_positioning_language_brand_communication",
        "state://lyra/r2-v0.1.0", "memory://lyra/r2-v0.1.0",
        "semantic_human_interface_stress",
    ),
    "SOFIA": LocalCognitiveProfile(
        "SOFIA", "identity://sofia", "identity://sofia",
        "software_implementation_code_incremental_integration",
        "state://sofia/r2-v0.1.0", "memory://sofia/r2-v0.1.0",
        "implementation_integration_adaptation_stress",
    ),
    "MÊTIS": LocalCognitiveProfile(
        "MÊTIS", "identity://metis", "identity://metis",
        "research_intelligence_strategy_market_hypotheses",
        "state://metis/r2-v0.1.0", "memory://metis/r2-v0.1.0",
        "implementation_integration_adaptation_stress",
    ),
    "ÁGORA": LocalCognitiveProfile(
        "ÁGORA", "identity://agora", "identity://agora",
        "technical_qa_software_audit_reproducibility_implementation_conformance",
        "state://agora/r2-v0.1.0", "memory://agora/r2-v0.1.0",
        "governance_evidence_stress",
    ),
    "AURI": LocalCognitiveProfile(
        "AURI", "identity://auri", "identity://auri",
        "administration_priority_continuity_system_of_record",
        "state://auri/r2-v0.1.0", "memory://auri/r2-v0.1.0",
        "governance_evidence_stress",
    ),
    "SYNERGEIA": LocalCognitiveProfile(
        "SYNERGEIA", "identity://synergeia", "identity://synergeia",
        "gtm_activation_distribution_channels_market_coordination",
        "state://synergeia/r2-v0.1.0", "memory://synergeia/r2-v0.1.0",
        "implementation_integration_adaptation_stress",
    ),
    "TÊMIS": LocalCognitiveProfile(
        "TÊMIS", "identity://temis", "REISOS::INST::ANDROID_PLAY::001",
        "android_google_play_stewardship",
        "state://temis/r2-v0.1.0", "memory://temis/r2-v0.1.0",
        "specialty_domain_transfer_stress",
    ),
}


def validate_local_profiles() -> None:
    if len(LOCAL_PROFILES) != 11:
        raise ValueError("eleven_local_profiles_required")
    if len({p.identity_ref for p in LOCAL_PROFILES.values()}) != 11:
        raise ValueError("local_profile_identity_isolation_required")
    if len({p.state_namespace for p in LOCAL_PROFILES.values()}) != 11:
        raise ValueError("local_profile_state_isolation_required")
    if len({p.memory_namespace for p in LOCAL_PROFILES.values()}) != 11:
        raise ValueError("local_profile_memory_isolation_required")
    if LOCAL_PROFILES["NÓESIS"].reference_role != "reference_pilot_only":
        raise ValueError("noesis_must_not_be_universal_template")
