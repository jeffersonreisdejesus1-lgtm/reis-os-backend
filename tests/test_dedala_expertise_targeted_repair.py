from __future__ import annotations

from dataclasses import replace

import pytest

from app.expertise.assurance import (
    FalsificationReceipt,
    VerificationReceipt,
    candidate_binding,
    evidence_binding,
    validate_falsification_receipt,
    validate_verification_receipt,
)
from app.expertise.corpus import DEDALA_EXPERT_FRAGMENTS, DEDALA_EXPERT_SOURCES
from app.expertise.derivation import draft_architectural_derivation
from app.expertise.registry import build_retrieval_plan
from app.expertise.retriever import retrieve_expert_evidence
from app.expertise.sources import validate_source_record

REVISION = "repair-revision-001"


def _candidate_and_evidence():
    plan = build_retrieval_plan("legacy architecture refactoring evolution")
    evidence = retrieve_expert_evidence(
        plan,
        DEDALA_EXPERT_SOURCES,
        DEDALA_EXPERT_FRAGMENTS,
    )
    candidate = draft_architectural_derivation(
        plan,
        evidence,
        "Prefer incremental refactoring.",
    )
    return candidate, evidence


def test_expected_family_removal_breaks_bounded_causal_chain() -> None:
    plan = build_retrieval_plan("legacy architecture refactoring evolution")
    sources = tuple(
        source
        for source in DEDALA_EXPERT_SOURCES
        if source.source_family != "FOWLER"
    )
    source_ids = {source.source_id for source in sources}
    fragments = tuple(
        fragment
        for fragment in DEDALA_EXPERT_FRAGMENTS
        if fragment.source_id in source_ids
    )
    assert retrieve_expert_evidence(plan, sources, fragments) == ()


def test_unrelated_family_with_matching_vocabulary_cannot_cross_lens_boundary() -> None:
    original = next(
        source
        for source in DEDALA_EXPERT_SOURCES
        if source.source_family == "KLEPPMANN"
    )
    forged_overlap = replace(
        original,
        retrieval_tags=("legacy", "architecture", "refactoring", "evolution"),
    )
    with pytest.raises(
        ValueError,
        match="expert_source_provenance_integrity_failure",
    ):
        validate_source_record(forged_overlap)


def test_falsification_receipt_is_bound_to_candidate_evidence_and_revision() -> None:
    candidate, evidence = _candidate_and_evidence()
    receipt = FalsificationReceipt(
        receipt_id="FALSIFY-BOUND-001",
        candidate_binding=candidate_binding(candidate),
        evidence_binding=evidence_binding(evidence),
        assessed_revision=REVISION,
        procedure_id="counterexample-search-v1",
        survived=True,
        evidence_refs=candidate.evidence_refs,
    )
    validate_falsification_receipt(receipt, candidate, evidence, REVISION)

    with pytest.raises(ValueError, match="falsification_receipt_revision_mismatch"):
        validate_falsification_receipt(receipt, candidate, evidence, "other-revision")
    with pytest.raises(ValueError, match="falsification_receipt_candidate_mismatch"):
        validate_falsification_receipt(
            replace(receipt, candidate_binding="0" * 64),
            candidate,
            evidence,
            REVISION,
        )
    with pytest.raises(ValueError, match="falsification_receipt_evidence_mismatch"):
        validate_falsification_receipt(
            replace(receipt, evidence_binding="0" * 64),
            candidate,
            evidence,
            REVISION,
        )


def test_verification_receipt_is_bound_to_candidate_evidence_and_revision() -> None:
    candidate, evidence = _candidate_and_evidence()
    receipt = VerificationReceipt(
        receipt_id="VERIFY-BOUND-001",
        candidate_binding=candidate_binding(candidate),
        evidence_binding=evidence_binding(evidence),
        assessed_revision=REVISION,
        procedure_id="evidence-integrity-check-v1",
        verified=True,
        evidence_refs=candidate.evidence_refs,
    )
    validate_verification_receipt(receipt, candidate, evidence, REVISION)
    with pytest.raises(ValueError, match="verification_receipt_refs_mismatch"):
        validate_verification_receipt(
            replace(receipt, evidence_refs=("wrong-ref",)),
            candidate,
            evidence,
            REVISION,
        )
