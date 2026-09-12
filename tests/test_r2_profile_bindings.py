from dataclasses import replace

import pytest

from app.profile_bindings.profiles import (
    KERNEL_INTERFACE_REF,
    OWNED_SYSTEM_ACCESS_CLASS,
    OWNED_SYSTEM_CAPABILITY_ADAPTERS,
    OWNED_SYSTEM_TOOL_PERMISSIONS,
    PROFILES,
    get_profile,
    validate_profiles,
)


def test_eleven_distinct_profiles_bind_same_frozen_kernel() -> None:
    validate_profiles()
    assert len(PROFILES) == 11
    assert {profile.kernel_interface_ref for profile in PROFILES.values()} == {
        KERNEL_INTERFACE_REF
    }
    assert len({profile.identity for profile in PROFILES.values()}) == 11
    assert len({profile.specialty for profile in PROFILES.values()}) == 11


def test_namespaces_are_ocs_local_and_isolated() -> None:
    state_namespaces = {
        profile.state_namespace for profile in PROFILES.values()
    }
    memory_namespaces = {
        profile.memory_namespace for profile in PROFILES.values()
    }
    assert len(state_namespaces) == 11
    assert len(memory_namespaces) == 11
    assert all(
        namespace.startswith("state://") for namespace in state_namespaces
    )
    assert all(
        namespace.startswith("memory://") for namespace in memory_namespaces
    )


def test_all_profiles_reference_explicit_authority_without_granting_it() -> None:
    for profile in PROFILES.values():
        assert profile.authority_envelope_ref.startswith("authority://")
        assert "authority_transfer=false" in profile.handoff_policy
        assert "memory_import=false" in profile.handoff_policy


def test_missing_authority_reference_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["SOFIA"] = replace(
        PROFILES["SOFIA"],
        authority_envelope_ref="",
    )
    with pytest.raises(
        ValueError,
        match="explicit_authority_reference_required",
    ):
        validate_profiles(profiles)


def test_cross_ocs_memory_namespace_merge_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["ÁGORA"] = replace(
        PROFILES["ÁGORA"],
        memory_namespace=PROFILES["SOFIA"].memory_namespace,
    )
    with pytest.raises(
        ValueError,
        match="memory_namespace_isolation_required",
    ):
        validate_profiles(profiles)


def test_identity_merge_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["LYRA"] = replace(
        PROFILES["LYRA"],
        identity=PROFILES["ÍRIS"].identity,
    )
    with pytest.raises(
        ValueError,
        match="profile_identity_merge_prohibited",
    ):
        validate_profiles(profiles)


def test_handoff_authority_transfer_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["AURI"] = replace(
        PROFILES["AURI"],
        handoff_policy=(
            "context_and_evidence_refs_only;"
            "authority_transfer=true;"
            "memory_import=false"
        ),
    )
    with pytest.raises(
        ValueError,
        match="handoff_authority_transfer_prohibited",
    ):
        validate_profiles(profiles)


def test_cross_ocs_memory_import_policy_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["MÊTIS"] = replace(
        PROFILES["MÊTIS"],
        handoff_policy=(
            "context_and_evidence_refs_only;"
            "authority_transfer=false;"
            "memory_import=true"
        ),
    )
    with pytest.raises(
        ValueError,
        match="cross_ocs_memory_import_prohibited",
    ):
        validate_profiles(profiles)


def test_unbound_or_unapproved_direct_route_is_rejected() -> None:
    profiles = dict(PROFILES)
    profiles["DÉDALA"] = replace(
        PROFILES["DÉDALA"],
        capability_adapters=("mutable.repo",),
        tool_permissions=("owned_system.read",),
    )
    with pytest.raises(
        ValueError,
        match="direct_effect_route_prohibited",
    ):
        validate_profiles(profiles)


def test_sofia_rejects_unapproved_adapter_even_with_owned_system_class() -> None:
    profiles = dict(PROFILES)
    profiles["SOFIA"] = replace(
        PROFILES["SOFIA"],
        capability_adapters=("mutable.repo",),
    )
    with pytest.raises(
        ValueError,
        match="unapproved_owned_system_adapter",
    ):
        validate_profiles(profiles)


def test_specialty_boundaries_match_noesis_manifest_and_themis_extension() -> None:
    assert "orchestration" in get_profile("NÓESIS").specialty
    assert "technical_architecture" in get_profile("DÉDALA").specialty
    assert (
        get_profile("SÝNESIS").specialty
        == "independent_institutional_assurance"
    )
    assert "ux_ui" in get_profile("ÍRIS").specialty
    assert "branding" in get_profile("LYRA").specialty
    assert "software_implementation" in get_profile("SOFIA").specialty
    assert "research_intelligence_strategy" in get_profile("MÊTIS").specialty
    assert "technical_qa" in get_profile("ÁGORA").specialty
    assert "administration" in get_profile("AURI").specialty
    assert "gtm_activation" in get_profile("SYNERGEIA").specialty
    assert (
        get_profile("TÊMIS").specialty
        == "android_google_play_stewardship"
    )
    assert get_profile("TÊMIS").identity == "identity://temis"


def test_self_assurance_denied_for_relevant_profiles() -> None:
    ocs_ids = (
        "NÓESIS",
        "DÉDALA",
        "SÝNESIS",
        "ÍRIS",
        "SOFIA",
        "ÁGORA",
        "TÊMIS",
    )
    for ocs_id in ocs_ids:
        assert "self_assurance" in get_profile(ocs_id).denied_action_classes


def test_sofia_owned_system_access_is_bounded_not_lateral() -> None:
    sofia = get_profile("SOFIA")
    assert "software_implementation_via_valid_envelope_lease_effector" in (
        sofia.allowed_action_classes
    )
    assert OWNED_SYSTEM_ACCESS_CLASS in sofia.allowed_action_classes
    assert "lateral_effect_route" in sofia.denied_action_classes
    assert set(sofia.capability_adapters).issubset(
        OWNED_SYSTEM_CAPABILITY_ADAPTERS
    )
    assert set(sofia.tool_permissions).issubset(
        OWNED_SYSTEM_TOOL_PERMISSIONS
    )
    assert "github.authenticated_connector" in sofia.capability_adapters
    assert "codemagic.authenticated_connector" in sofia.capability_adapters
    assert "owned_system.read" in sofia.tool_permissions
    assert "owned_system.build_trigger" in sofia.tool_permissions
