from app.cognitive_validation import (
    AB0_REQUIRED_DEFINITIONS,
    CognitiveClaim,
    CognitiveValidationContract,
    canonical_ab0_contract,
)


def test_ab0_required_definition_set_is_complete():
    assert set(AB0_REQUIRED_DEFINITIONS) == set(CognitiveClaim)
    assert len(AB0_REQUIRED_DEFINITIONS) == 11


def test_canonical_ab0_contract_passes_fail_closed_invariants():
    valid, violations = canonical_ab0_contract().validate()
    assert valid is True
    assert violations == ()


def test_learning_cannot_expand_authority():
    valid, violations = CognitiveValidationContract(
        learning_may_expand_authority=True
    ).validate()
    assert valid is False
    assert "LEARNING != AUTHORITY_EXPANSION" in violations


def test_unverified_feedback_must_be_quarantined():
    valid, violations = CognitiveValidationContract(
        unverified_feedback_quarantined=False
    ).validate()
    assert valid is False
    assert "UNVERIFIED_FEEDBACK -> QUARANTINE" in violations


def test_stale_generation_cognitive_commit_must_be_denied():
    valid, violations = CognitiveValidationContract(
        stale_generation_commit_denied=False
    ).validate()
    assert valid is False
    assert "STALE_GENERATION -> COGNITIVE_COMMIT_DENIED" in violations
