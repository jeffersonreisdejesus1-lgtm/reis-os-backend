from app.profile_bindings.cupuwa_visual_profiles import (
    CUPUWA_VISUAL_PROFILES,
    validate_cupuwa_visual_profiles,
)
from app.profile_bindings.profiles import KERNEL_INTERFACE_REF, PROFILES


def test_cupuwa_visual_pack_has_nineteen_new_specialists_plus_canonical_iris() -> None:
    validate_cupuwa_visual_profiles()
    assert len(CUPUWA_VISUAL_PROFILES) == 19
    assert "ÍRIS" in PROFILES
    assert "ÍRIS" not in CUPUWA_VISUAL_PROFILES


def test_visual_profiles_inherit_universal_kernel_and_isolated_namespaces() -> None:
    profiles = tuple(CUPUWA_VISUAL_PROFILES.values())
    assert {p.kernel_interface_ref for p in profiles} == {KERNEL_INTERFACE_REF}
    assert len({p.identity for p in profiles}) == 19
    assert len({p.state_namespace for p in profiles}) == 19
    assert len({p.memory_namespace for p in profiles}) == 19


def test_visual_profiles_preserve_authority_and_memory_handoff_invariants() -> None:
    for profile in CUPUWA_VISUAL_PROFILES.values():
        assert profile.authority_envelope_ref.startswith("authority://")
        assert "authority_transfer=false" in profile.handoff_policy
        assert "memory_import=false" in profile.handoff_policy
        assert profile.capability_adapters == ()
        assert profile.tool_permissions == ()


def test_production_and_independent_quality_roles_are_separated() -> None:
    for ocs_id in ("HÉSTIA", "ROTA", "PRÁXIS", "MORPHÉ"):
        assert "self_assurance" in CUPUWA_VISUAL_PROFILES[ocs_id].denied_action_classes
    for ocs_id in ("ARGOS", "DOKIMÉ", "KRITÉRION"):
        profile = CUPUWA_VISUAL_PROFILES[ocs_id]
        assert "self_assurance" in profile.denied_action_classes
        assert any("verification" in action or "judgment" in action for action in profile.allowed_action_classes)


def test_material_ui_roles_remain_kernel_mediated() -> None:
    for ocs_id in ("HÉSTIA", "ROTA", "PRÁXIS", "MORPHÉ"):
        profile = CUPUWA_VISUAL_PROFILES[ocs_id]
        assert any("valid_envelope_lease_effector" in action for action in profile.allowed_action_classes)
        assert "lateral_effect_route" in profile.denied_action_classes
