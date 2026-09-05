from dataclasses import replace

import pytest

from app.expertise.derivation import (
    DERIVATION_FALSIFICATION_FAILED,
    DERIVATION_FALSIFICATION_SURVIVED,
    DERIVATION_PERSISTENCE_ELIGIBLE,
    DERIVATION_VERIFIED,
    assert_persistence_eligible,
    draft_architectural_derivation,
    record_falsification,
    record_verification,
)
from app.expertise.registry import build_retrieval_plan
from app.expertise.retriever import RetrievedExpertEvidence


def _evidence() -> tuple[RetrievedExpertEvidence, ...]:
    return (
        RetrievedExpertEvidence(
            source_id="SRC-001",
            fragment_id="FRAG-001",
            locator="chapter:1",
            content="bounded technical evidence",
            source_class="RETRIEVABLE_EXTERNAL_TECHNICAL_SOURCE",
            applicability_score=2,
        ),
    )


def test_derivation_starts_non_authoritative_and_non_canonical() -> None:
    plan = build_retrieval_plan("architecture refactoring evolution")
    candidate = draft_architectural_derivation(
        plan,
        _evidence(),
        "Prefer an incremental refactoring boundary.",
    )

    assert candidate.ocs_id == "DÉDALA"
    assert candidate.identity_effect == "NONE"
    assert candidate.authority_effect == "NONE"
    assert candidate.canon_effect == "NONE"
    assert candidate.persistence_status == "NOT_ELIGIBLE"
    assert candidate.evidence_refs == ("SRC-001:FRAG-001@chapter:1",)


def test_derivation_requires_retrieved_evidence() -> None:
    plan = build_retrieval_plan("architecture refactoring")
    with pytest.raises(ValueError, match="derivation_requires_retrieved_evidence"):
        draft_architectural_derivation(plan, (), "candidate")


def test_failed_falsification_blocks_verification_and_persistence() -> None:
    plan = build_retrieval_plan("architecture refactoring")
    candidate = draft_architectural_derivation(plan, _evidence(), "candidate")
    failed = record_falsification(candidate, survived=False)

    assert failed.falsification_status == DERIVATION_FALSIFICATION_FAILED
    with pytest.raises(
        ValueError, match="verification_requires_survived_falsification"
    ):
        record_verification(failed, verified=True)
    with pytest.raises(
        ValueError, match="persistence_requires_survived_falsification"
    ):
        assert_persistence_eligible(failed)


def test_survived_falsification_then_verification_allows_persistence_only() -> None:
    plan = build_retrieval_plan("architecture refactoring")
    candidate = draft_architectural_derivation(plan, _evidence(), "candidate")
    survived = record_falsification(candidate, survived=True)
    verified = record_verification(survived, verified=True)

    assert survived.falsification_status == DERIVATION_FALSIFICATION_SURVIVED
    assert verified.verification_status == DERIVATION_VERIFIED
    assert verified.persistence_status == DERIVATION_PERSISTENCE_ELIGIBLE
    assert verified.authority_effect == "NONE"
    assert verified.canon_effect == "NONE"
    assert_persistence_eligible(verified)


def test_tampered_candidate_cannot_gain_authority_or_canon() -> None:
    plan = build_retrieval_plan("architecture refactoring")
    candidate = draft_architectural_derivation(plan, _evidence(), "candidate")
    survived = record_falsification(candidate, survived=True)
    verified = record_verification(survived, verified=True)

    with pytest.raises(ValueError, match="derivation_must_not_create_authority"):
        assert_persistence_eligible(replace(verified, authority_effect="GRANT"))
    with pytest.raises(ValueError, match="derivation_must_not_create_canon"):
        assert_persistence_eligible(replace(verified, canon_effect="PROMOTE"))
