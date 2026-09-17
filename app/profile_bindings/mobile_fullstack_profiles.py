from __future__ import annotations

from app.profile_bindings.profiles import OCSProfile, _profile

PACK_ID = "REIS-OS-MOBILE-FULLSTACK-OCS-PACK-001"
PACK_VERSION = "v0.1.0"

DENY_BUILD = ("self_assurance", "authority_expansion", "lateral_effect_route")
DENY_VERIFY = ("primary_construction_under_verification", "self_assurance", "automatic_promotion")
DENY_ADVISE = ("unmediated_material_effect", "self_assurance", "authority_expansion")


def _p(ocs_id: str, specialty: str, allowed: tuple[str, ...], support: tuple[str, ...], denied: tuple[str, ...] = DENY_ADVISE) -> OCSProfile:
    return _profile(ocs_id, specialty, allowed, denied, support)


# 42 specialists complete the existing 30-OCS roster into a 72-OCS mobile
# software organization. Profiles remain authority-neutral: runtime effect
# adapters and tool permissions are bound separately by governed execution.
MOBILE_FULLSTACK_PROFILES: dict[str, OCSProfile] = {
    # Product / requirements / domain
    "AXÍA": _p("AXÍA", "product_value_outcomes_scope_prioritization", ("product_outcome_analysis", "scope_contract"), ("product", "value", "scope")),
    "HOROS": _p("HOROS", "requirements_acceptance_criteria_traceability", ("requirements_specification", "acceptance_contract"), ("requirements", "acceptance", "traceability")),
    "ODÓS": _p("ODÓS", "user_journeys_flows_use_cases_edge_cases", ("journey_specification", "edge_case_analysis"), ("journeys", "flows", "use_cases")),
    "DOMÉA": _p("DOMÉA", "domain_model_business_rules_invariants", ("domain_model_specification", "business_rule_analysis"), ("domain", "business_rules", "invariants")),
    "NOMÍSMA": _p("NOMÍSMA", "financial_domain_money_ledger_precision_reconciliation", ("financial_domain_specification", "ledger_rule_analysis"), ("money", "ledger", "precision", "reconciliation")),
    "EMPIRÍA": _p("EMPIRÍA", "product_research_user_evidence_hypothesis_validation", ("product_research", "hypothesis_evidence"), ("research", "user_evidence", "hypotheses")),

    # Shared mobile engineering
    "ARCHÉ": _p("ARCHÉ", "mobile_application_architecture_modularity_boundaries", ("mobile_architecture_design", "module_boundary_specification"), ("mobile_architecture", "modularity", "boundaries")),
    "STÁTE": _p("STÁTE", "application_state_unidirectional_flow_lifecycle_state", ("state_model_specification", "state_flow_implementation_via_valid_envelope_lease_effector"), ("state", "state_flow", "lifecycle"), DENY_BUILD),
    "MNÉME": _p("MNÉME", "local_persistence_database_cache_migrations", ("persistence_implementation_via_valid_envelope_lease_effector", "migration_specification"), ("database", "persistence", "cache", "migrations"), DENY_BUILD),
    "DIKTYO": _p("DIKTYO", "networking_http_api_transport_resilience", ("networking_implementation_via_valid_envelope_lease_effector", "transport_contract"), ("networking", "http", "api_transport", "resilience"), DENY_BUILD),
    "SYNCHRÓN": _p("SYNCHRÓN", "offline_first_sync_conflict_resolution_consistency", ("sync_implementation_via_valid_envelope_lease_effector", "conflict_policy_specification"), ("offline_first", "sync", "conflicts", "consistency"), DENY_BUILD),
    "SÝNDESI": _p("SÝNDESI", "mobile_external_integrations_sdk_service_binding", ("integration_implementation_via_valid_envelope_lease_effector", "sdk_integration_analysis"), ("integrations", "sdk", "services"), DENY_BUILD),

    # Android engineering (TÊMIS retains Play stewardship/compliance)
    "KOTLIN": _p("KOTLIN", "android_kotlin_language_coroutines_type_safe_engineering", ("android_kotlin_implementation_via_valid_envelope_lease_effector",), ("android", "kotlin", "coroutines"), DENY_BUILD),
    "COMPOSÉ": _p("COMPOSÉ", "android_jetpack_compose_ui_runtime_state", ("compose_implementation_via_valid_envelope_lease_effector",), ("android", "jetpack_compose", "ui_runtime"), DENY_BUILD),
    "DROÍD": _p("DROÍD", "android_platform_lifecycle_services_permissions_components", ("android_platform_implementation_via_valid_envelope_lease_effector",), ("android_platform", "lifecycle", "services", "permissions"), DENY_BUILD),
    "GRADLE": _p("GRADLE", "android_gradle_build_variants_dependencies_toolchain", ("android_build_configuration_via_valid_envelope_lease_effector",), ("gradle", "android_build", "dependencies"), DENY_BUILD),
    "FORMA": _p("FORMA", "android_devices_form_factors_windowing_density_compatibility", ("android_form_factor_implementation_via_valid_envelope_lease_effector",), ("android_devices", "form_factors", "compatibility"), DENY_BUILD),

    # iOS engineering and stewardship
    "SWIFT": _p("SWIFT", "ios_swift_language_concurrency_type_safe_engineering", ("ios_swift_implementation_via_valid_envelope_lease_effector",), ("ios", "swift", "concurrency"), DENY_BUILD),
    "SWIFTUI": _p("SWIFTUI", "ios_swiftui_uikit_interface_state_navigation", ("ios_ui_implementation_via_valid_envelope_lease_effector",), ("ios", "swiftui", "uikit", "navigation"), DENY_BUILD),
    "CUPERTINO": _p("CUPERTINO", "ios_platform_lifecycle_entitlements_services_devices", ("ios_platform_implementation_via_valid_envelope_lease_effector",), ("ios_platform", "lifecycle", "entitlements", "devices"), DENY_BUILD),
    "XCODE": _p("XCODE", "ios_xcode_spm_build_signing_toolchain", ("ios_build_configuration_via_valid_envelope_lease_effector",), ("xcode", "spm", "ios_build", "signing"), DENY_BUILD),
    "APPLÉIA": _p("APPLÉIA", "apple_app_store_testflight_privacy_review_distribution_stewardship", ("app_store_readiness_review", "apple_privacy_review", "testflight_distribution_analysis"), ("apple", "app_store", "testflight", "privacy", "distribution"), ("primary_software_implementation", "self_assurance", "unmediated_publication", "credential_access_by_profile", "authority_creation", "automatic_promotion")),

    # Backend / data / identity
    "APÍON": _p("APÍON", "backend_api_contracts_versioning_error_semantics", ("api_contract_design", "api_implementation_via_valid_envelope_lease_effector"), ("backend", "api", "contracts", "versioning"), DENY_BUILD),
    "DATON": _p("DATON", "data_model_database_schema_queries_integrity", ("data_model_design", "database_implementation_via_valid_envelope_lease_effector"), ("data", "database", "schema", "integrity"), DENY_BUILD),
    "AUTHÉN": _p("AUTHÉN", "identity_authentication_authorization_session_management", ("identity_security_design", "auth_implementation_via_valid_envelope_lease_effector"), ("authentication", "authorization", "sessions"), DENY_BUILD),
    "SERVÍA": _p("SERVÍA", "backend_services_jobs_events_mobile_integration", ("backend_service_implementation_via_valid_envelope_lease_effector",), ("services", "jobs", "events", "mobile_backend"), DENY_BUILD),

    # Security / privacy
    "THREAT": _p("THREAT", "mobile_threat_model_attack_surface_abuse_cases", ("threat_model", "abuse_case_analysis"), ("security", "threat_model", "attack_surface")),
    "KRYPTÓ": _p("KRYPTÓ", "mobile_crypto_key_storage_secret_protection", ("crypto_storage_design", "secret_protection_review"), ("cryptography", "key_storage", "secrets")),
    "ASPÍS": _p("ASPÍS", "mobile_platform_network_code_resilience_security", ("mobile_security_review", "security_control_specification"), ("platform_security", "network_security", "resilience")),
    "PRIVÁTA": _p("PRIVÁTA", "privacy_data_minimization_consent_retention_disclosure", ("privacy_analysis", "data_governance_specification"), ("privacy", "consent", "retention", "data_minimization")),

    # Test / quality
    "MONÁDA": _p("MONÁDA", "unit_testing_property_testing_domain_correctness", ("independent_unit_test_design", "property_test_design"), ("unit_tests", "property_tests", "correctness"), DENY_VERIFY),
    "SÝMPLEX": _p("SÝMPLEX", "integration_contract_component_testing", ("independent_integration_verification", "contract_test_design"), ("integration_tests", "contract_tests"), DENY_VERIFY),
    "TELOS": _p("TELOS", "mobile_end_to_end_ui_automation_real_journey_testing", ("independent_e2e_verification", "ui_automation_test_design"), ("e2e", "ui_automation", "journeys"), DENY_VERIFY),
    "A11Y": _p("A11Y", "mobile_accessibility_semantics_screen_reader_input_audit", ("independent_accessibility_verification", "accessibility_defect_report"), ("accessibility", "semantics", "screen_reader"), DENY_VERIFY),
    "ANTÍPALOS": _p("ANTÍPALOS", "adversarial_regression_fault_injection_bypass_testing", ("independent_adversarial_verification", "fault_injection_analysis"), ("adversarial", "regression", "fault_injection"), DENY_VERIFY),

    # Performance / reliability / observability
    "TÁCHOS": _p("TÁCHOS", "mobile_performance_startup_rendering_latency_profiling", ("performance_analysis", "performance_budget_specification"), ("performance", "startup", "rendering", "latency")),
    "MNEMOS": _p("MNEMOS", "mobile_memory_leaks_allocations_resource_pressure", ("memory_profile_analysis", "resource_pressure_analysis"), ("memory", "leaks", "allocations")),
    "ENERGEIA": _p("ENERGEIA", "mobile_battery_background_work_network_energy", ("energy_profile_analysis", "battery_budget_specification"), ("battery", "background_work", "energy")),
    "PHAROS": _p("PHAROS", "mobile_observability_crash_anr_logs_metrics_diagnostics", ("observability_specification", "crash_anr_analysis"), ("observability", "crash", "anr", "diagnostics")),

    # Delivery / release
    "PIPELINE": _p("PIPELINE", "mobile_ci_cd_build_test_artifact_pipeline", ("ci_cd_configuration_via_valid_envelope_lease_effector",), ("ci_cd", "build", "test_pipeline", "artifacts"), DENY_BUILD),
    "KLEIS": _p("KLEIS", "signing_credentials_secrets_provisioning_release_security", ("signing_readiness_analysis", "credential_boundary_specification"), ("signing", "credentials", "provisioning", "release_security")),

    # Embedded AI
    "MIKRÓN": _p("MIKRÓN", "on_device_model_selection_quantization_inference_benchmarking", ("local_model_analysis", "on_device_inference_specification"), ("local_ai", "models", "quantization", "inference")),
    "NEURÁ": _p("NEURÁ", "mobile_ai_runtime_context_safety_product_integration", ("mobile_ai_integration_design", "ai_runtime_implementation_via_valid_envelope_lease_effector"), ("mobile_ai", "runtime", "context", "safety"), DENY_BUILD),
}


def validate_mobile_fullstack_profiles() -> None:
    if len(MOBILE_FULLSTACK_PROFILES) != 42:
        raise ValueError("forty_two_mobile_fullstack_profiles_required")
    profiles = tuple(MOBILE_FULLSTACK_PROFILES.values())
    if len({p.identity for p in profiles}) != 42:
        raise ValueError("profile_identity_merge_prohibited")
    if len({p.state_namespace for p in profiles}) != 42:
        raise ValueError("state_namespace_isolation_required")
    if len({p.memory_namespace for p in profiles}) != 42:
        raise ValueError("memory_namespace_isolation_required")
    if len({p.specialty for p in profiles}) != 42:
        raise ValueError("specialty_collision_prohibited")
    for profile in profiles:
        if "authority_transfer=false" not in profile.handoff_policy:
            raise ValueError("handoff_authority_transfer_prohibited")
        if "memory_import=false" not in profile.handoff_policy:
            raise ValueError("cross_ocs_memory_import_prohibited")
        if profile.capability_adapters or profile.tool_permissions:
            raise ValueError("direct_effect_route_prohibited")
