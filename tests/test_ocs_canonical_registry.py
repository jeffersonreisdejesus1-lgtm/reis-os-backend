from app.profile_bindings.canonical_registry import (
    CANONICAL_OCS_REGISTRY,
    EXPECTED_OCS_IDS,
    TEMIS,
    get_canonical_profile,
    validate_canonical_registry,
)
from app.profile_bindings.mobile_fullstack_profiles import (
    MOBILE_FULLSTACK_PROFILES,
    validate_mobile_fullstack_profiles,
)
from app.profile_bindings.profiles import KERNEL_INTERFACE_REF, PROFILES


def test_registry_canonicalizes_all_seventy_two_ocs() -> None:
    validate_mobile_fullstack_profiles()
    validate_canonical_registry()
    assert len(CANONICAL_OCS_REGISTRY) == 72
    assert set(CANONICAL_OCS_REGISTRY) == EXPECTED_OCS_IDS
    assert len(MOBILE_FULLSTACK_PROFILES) == 42


def test_foundation_ten_remain_intact_as_historical_generation() -> None:
    for ocs_id, profile in PROFILES.items():
        assert CANONICAL_OCS_REGISTRY[ocs_id] == profile


def test_temis_is_canonical_android_play_stewardship_ocs() -> None:
    assert get_canonical_profile("TÊMIS") is TEMIS
    assert "android_google_play" in TEMIS.specialty
    assert "privacy" in TEMIS.specialty
    assert "unmediated_publication" in TEMIS.denied_action_classes
    assert "credential_access_by_profile" in TEMIS.denied_action_classes


def test_apple_has_independent_app_store_stewardship_ocs() -> None:
    apple = get_canonical_profile("APPLÉIA")
    assert "apple_app_store" in apple.specialty
    assert "testflight" in apple.specialty
    assert "unmediated_publication" in apple.denied_action_classes
    assert "credential_access_by_profile" in apple.denied_action_classes


def test_every_canonical_ocs_has_isolated_identity_state_memory_and_specialty() -> None:
    profiles = tuple(CANONICAL_OCS_REGISTRY.values())
    assert len({p.identity for p in profiles}) == 72
    assert len({p.state_namespace for p in profiles}) == 72
    assert len({p.memory_namespace for p in profiles}) == 72
    assert len({p.specialty for p in profiles}) == 72


def test_every_canonical_ocs_inherits_same_universal_kernel_contract() -> None:
    for profile in CANONICAL_OCS_REGISTRY.values():
        assert profile.kernel_interface_ref == KERNEL_INTERFACE_REF
        assert profile.authority_envelope_ref.startswith("authority://")
        assert "authority_transfer=false" in profile.handoff_policy
        assert "memory_import=false" in profile.handoff_policy
        assert profile.capability_adapters == ()
        assert profile.tool_permissions == ()
