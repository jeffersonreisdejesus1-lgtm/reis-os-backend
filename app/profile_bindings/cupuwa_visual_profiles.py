from __future__ import annotations

from app.profile_bindings.profiles import OCSProfile, _profile

PACK_ID = "CUPUWA-VISUAL-PRODUCT-OCS-PACK-001"
PACK_VERSION = "v0.1.0"


def _visual_profile(
    ocs_id: str,
    specialty: str,
    allowed: tuple[str, ...],
    denied: tuple[str, ...],
    support: tuple[str, ...],
) -> OCSProfile:
    """Bind a CUPUWA specialist to the same universal OCS profile physiology."""
    return _profile(ocs_id, specialty, allowed, denied, support)


# ÍRIS is already canonical in PROFILES. This pack binds the 19 additional
# specialist OCS identities required by the CUPUWA visual/product cell.
CUPUWA_VISUAL_PROFILES: dict[str, OCSProfile] = {
    "AURA": _visual_profile(
        "AURA", "visual_art_direction_product_aesthetics",
        ("visual_direction", "art_direction_artifact"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("art_direction", "visual_language", "aesthetics"),
    ),
    "EIKÓN": _visual_profile(
        "EIKÓN", "ui_design_screen_hierarchy_visual_states",
        ("ui_design", "screen_specification", "visual_state_design"),
        ("requirements_rewrite_by_inference", "self_assurance", "authority_expansion"),
        ("ui", "screen_design", "visual_hierarchy"),
    ),
    "TÝPOS": _visual_profile(
        "TÝPOS", "design_system_tokens_components_patterns",
        ("design_system_specification", "component_contract_design"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("design_system", "tokens", "components"),
    ),
    "GRAMMÉ": _visual_profile(
        "GRAMMÉ", "layout_grid_spacing_density_composition",
        ("layout_specification", "grid_analysis"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("layout", "grid", "spacing", "composition"),
    ),
    "LÉXIS": _visual_profile(
        "LÉXIS", "ux_writing_microcopy_labels_errors_onboarding_copy",
        ("ux_copy_artifact", "microcopy_specification"),
        ("functional_behavior_change_by_copy", "self_assurance", "authority_expansion"),
        ("ux_writing", "microcopy", "content_design"),
    ),
    "CHRÔMA": _visual_profile(
        "CHRÔMA", "color_system_contrast_semantic_states",
        ("color_system_specification", "contrast_analysis"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("color", "contrast", "semantic_color"),
    ),
    "SÊMA": _visual_profile(
        "SÊMA", "iconography_symbolic_language_visual_semantics",
        ("icon_system_specification", "symbolic_language_artifact"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("iconography", "symbols", "visual_semantics"),
    ),
    "KINÉSIS": _visual_profile(
        "KINÉSIS", "motion_design_transitions_microinteractions_feedback",
        ("motion_specification", "microinteraction_design"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("motion", "transitions", "microinteractions"),
    ),
    "FIGMA": _visual_profile(
        "FIGMA", "figma_design_materialization_prototyping",
        ("design_materialization", "prototype_artifact"),
        ("unspecified_design_invention", "self_assurance", "authority_expansion"),
        ("figma", "prototype", "design_artifact"),
    ),
    "DÉSMOS": _visual_profile(
        "DÉSMOS", "figma_component_engineering_variants_variables",
        ("figma_component_artifact", "design_token_binding"),
        ("primary_software_implementation", "self_assurance", "authority_expansion"),
        ("figma_components", "variants", "variables"),
    ),
    "GÉPHYRA": _visual_profile(
        "GÉPHYRA", "design_to_code_mapping_implementation_specification",
        ("design_code_mapping", "implementation_specification"),
        ("self_fidelity_assurance", "unmediated_material_effect", "authority_expansion"),
        ("design_to_code", "mapping", "implementation_spec"),
    ),
    "HÉSTIA": _visual_profile(
        "HÉSTIA", "mobile_ui_engineering_interface_materialization",
        ("mobile_ui_implementation_via_valid_envelope_lease_effector",),
        ("self_assurance", "architecture_rewrite_without_authority", "lateral_effect_route"),
        ("mobile_ui", "interface_implementation", "components"),
    ),
    "ROTA": _visual_profile(
        "ROTA", "mobile_navigation_routes_back_stack_destination_behavior",
        ("navigation_implementation_via_valid_envelope_lease_effector",),
        ("self_assurance", "product_scope_expansion", "lateral_effect_route"),
        ("navigation", "routes", "back_stack"),
    ),
    "PRÁXIS": _visual_profile(
        "PRÁXIS", "interaction_engineering_inputs_keyboard_forms_gestures_feedback",
        ("interaction_implementation_via_valid_envelope_lease_effector",),
        ("self_assurance", "domain_rule_rewrite_without_authority", "lateral_effect_route"),
        ("interaction", "inputs", "forms", "keyboard"),
    ),
    "MORPHÉ": _visual_profile(
        "MORPHÉ", "responsive_ui_viewport_density_orientation_overflow",
        ("responsive_ui_implementation_via_valid_envelope_lease_effector",),
        ("self_assurance", "product_scope_expansion", "lateral_effect_route"),
        ("responsive_ui", "viewport", "density", "layout_adaptation"),
    ),
    "ARGOS": _visual_profile(
        "ARGOS", "independent_visual_qa_design_implementation_fidelity",
        ("independent_visual_verification", "visual_defect_report"),
        ("primary_construction_under_verification", "self_assurance", "promotion"),
        ("visual_qa", "fidelity", "visual_regression"),
    ),
    "DOKIMÉ": _visual_profile(
        "DOKIMÉ", "independent_ux_qa_journey_friction_behavior_validation",
        ("independent_ux_verification", "ux_defect_report"),
        ("primary_construction_under_verification", "self_assurance", "promotion"),
        ("ux_qa", "journeys", "friction", "behavior"),
    ),
    "LEÍA": _visual_profile(
        "LEÍA", "product_polish_finish_consistency_perceived_quality",
        ("product_polish_analysis", "polish_remediation_requirements"),
        ("primary_software_implementation", "self_assurance", "promotion"),
        ("polish", "finish", "consistency", "perceived_quality"),
    ),
    "KRITÉRION": _visual_profile(
        "KRITÉRION", "integrated_product_quality_readiness_evaluation",
        ("product_quality_verification", "readiness_judgment"),
        ("primary_construction_under_verification", "self_assurance", "automatic_promotion"),
        ("product_quality", "readiness", "integrated_quality"),
    ),
}


def validate_cupuwa_visual_profiles() -> None:
    expected = {
        "AURA", "EIKÓN", "TÝPOS", "GRAMMÉ", "LÉXIS", "CHRÔMA", "SÊMA",
        "KINÉSIS", "FIGMA", "DÉSMOS", "GÉPHYRA", "HÉSTIA", "ROTA", "PRÁXIS",
        "MORPHÉ", "ARGOS", "DOKIMÉ", "LEÍA", "KRITÉRION",
    }
    if set(CUPUWA_VISUAL_PROFILES) != expected:
        raise ValueError("cupuwa_visual_profile_set_mismatch")
    profiles = tuple(CUPUWA_VISUAL_PROFILES.values())
    if len({p.identity for p in profiles}) != len(profiles):
        raise ValueError("profile_identity_merge_prohibited")
    if len({p.state_namespace for p in profiles}) != len(profiles):
        raise ValueError("state_namespace_isolation_required")
    if len({p.memory_namespace for p in profiles}) != len(profiles):
        raise ValueError("memory_namespace_isolation_required")
    for profile in profiles:
        if not profile.authority_envelope_ref:
            raise ValueError("explicit_authority_reference_required")
        if "authority_transfer=false" not in profile.handoff_policy:
            raise ValueError("handoff_authority_transfer_prohibited")
        if "memory_import=false" not in profile.handoff_policy:
            raise ValueError("cross_ocs_memory_import_prohibited")
        if profile.capability_adapters or profile.tool_permissions:
            raise ValueError("direct_effect_route_prohibited")
