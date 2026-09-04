import pytest

from app.expertise.registry import (
    AUTHORITY_EFFECT_NONE,
    DEDALA_EXPERTISE_MANIFEST,
    ExpertiseManifest,
    build_retrieval_plan,
    validate_manifest,
)


def test_dedala_manifest_is_optional_specialty_capability() -> None:
    validate_manifest(DEDALA_EXPERTISE_MANIFEST)
    assert DEDALA_EXPERTISE_MANIFEST.ocs_id == "DÉDALA"
    assert (
        DEDALA_EXPERTISE_MANIFEST.capability_status
        == "OPTIONAL_SPECIALTY_CAPABILITY"
    )
    assert DEDALA_EXPERTISE_MANIFEST.identity_effect == "NONE"
    assert DEDALA_EXPERTISE_MANIFEST.authority_effect == AUTHORITY_EFFECT_NONE
    assert DEDALA_EXPERTISE_MANIFEST.canon_effect == "NONE"


def test_problem_selects_distributed_state_and_messaging_lenses() -> None:
    plan = build_retrieval_plan(
        "Hazel Kernel distributed state consistency causality recovery "
        "message retry delivery"
    )
    assert plan.candidate_lenses[0] == "DATA_CONSISTENCY_CAUSALITY"
    assert "MESSAGE_INTEGRATION_ROUTING" in plan.candidate_lenses
    assert plan.authority_effect == "NONE"
    assert plan.derivation_status == "LOCAL_ARCHITECTURAL_DERIVATION_CANDIDATE"


def test_refactoring_and_boundary_problem_selects_lenses() -> None:
    plan = build_retrieval_plan(
        "refactor legacy architecture boundaries coupling migration "
        "without a monolith"
    )
    assert "ARCH_REFACTORING_EVOLUTION" in plan.candidate_lenses
    assert "BOUNDARY_DECOMPOSITION_COUPLING" in plan.candidate_lenses


def test_expertise_cannot_be_rebound_to_another_ocs() -> None:
    invalid = ExpertiseManifest(
        ocs_id="NÓESIS",
        capability_status="OPTIONAL_SPECIALTY_CAPABILITY",
        lenses=DEDALA_EXPERTISE_MANIFEST.lenses,
    )
    with pytest.raises(ValueError, match="dedala_first_implementation_only"):
        validate_manifest(invalid)


def test_expertise_cannot_create_authority() -> None:
    invalid = ExpertiseManifest(
        ocs_id="DÉDALA",
        capability_status="OPTIONAL_SPECIALTY_CAPABILITY",
        lenses=DEDALA_EXPERTISE_MANIFEST.lenses,
        authority_effect="EXPAND",
    )
    with pytest.raises(
        ValueError,
        match="expertise_must_not_create_authority",
    ):
        validate_manifest(invalid)


def test_unmatched_problem_does_not_invent_an_expert() -> None:
    plan = build_retrieval_plan("completely unrelated lexical material")
    assert plan.candidate_lenses == ()
    assert plan.retrieval_queries == ()
