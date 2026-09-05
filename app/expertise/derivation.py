from __future__ import annotations

from dataclasses import dataclass, replace

from .registry import LOCAL_DERIVATION_INITIAL_STATUS, RetrievalPlan
from .retriever import RetrievedExpertEvidence

DERIVATION_FALSIFICATION_PENDING = "FALSIFICATION_PENDING"
DERIVATION_FALSIFICATION_SURVIVED = "FALSIFICATION_SURVIVED"
DERIVATION_FALSIFICATION_FAILED = "FALSIFICATION_FAILED"
DERIVATION_VERIFICATION_PENDING = "VERIFICATION_PENDING"
DERIVATION_VERIFIED = "VERIFIED"
DERIVATION_PERSISTENCE_ELIGIBLE = "PERSISTENCE_ELIGIBLE"


@dataclass(frozen=True)
class ArchitecturalDerivationCandidate:
    ocs_id: str
    problem: str
    proposition: str
    candidate_lenses: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    derivation_status: str = LOCAL_DERIVATION_INITIAL_STATUS
    falsification_status: str = DERIVATION_FALSIFICATION_PENDING
    verification_status: str = DERIVATION_VERIFICATION_PENDING
    persistence_status: str = "NOT_ELIGIBLE"
    identity_effect: str = "NONE"
    authority_effect: str = "NONE"
    canon_effect: str = "NONE"


def _evidence_ref(item: RetrievedExpertEvidence) -> str:
    return f"{item.source_id}:{item.fragment_id}@{item.locator}"


def draft_architectural_derivation(
    plan: RetrievalPlan,
    evidence: tuple[RetrievedExpertEvidence, ...],
    proposition: str,
) -> ArchitecturalDerivationCandidate:
    if plan.ocs_id != "DÉDALA":
        raise ValueError("dedala_first_implementation_only")
    if plan.authority_effect != "NONE":
        raise ValueError("derivation_must_not_expand_authority")
    if not proposition.strip():
        raise ValueError("derivation_requires_proposition")
    if not evidence:
        raise ValueError("derivation_requires_retrieved_evidence")
    for item in evidence:
        if item.authority_effect != "NONE":
            raise ValueError("expert_evidence_must_not_create_authority")
        if item.canon_effect != "NONE":
            raise ValueError("expert_evidence_must_not_create_canon")
    refs = tuple(dict.fromkeys(_evidence_ref(item) for item in evidence))
    return ArchitecturalDerivationCandidate(
        ocs_id=plan.ocs_id,
        problem=plan.problem,
        proposition=proposition.strip(),
        candidate_lenses=plan.candidate_lenses,
        evidence_refs=refs,
    )


def record_falsification(
    candidate: ArchitecturalDerivationCandidate,
    *,
    survived: bool,
) -> ArchitecturalDerivationCandidate:
    if candidate.falsification_status != DERIVATION_FALSIFICATION_PENDING:
        raise ValueError("falsification_already_recorded")
    status = (
        DERIVATION_FALSIFICATION_SURVIVED
        if survived
        else DERIVATION_FALSIFICATION_FAILED
    )
    return replace(candidate, falsification_status=status)


def record_verification(
    candidate: ArchitecturalDerivationCandidate,
    *,
    verified: bool,
) -> ArchitecturalDerivationCandidate:
    if candidate.falsification_status != DERIVATION_FALSIFICATION_SURVIVED:
        raise ValueError("verification_requires_survived_falsification")
    if candidate.verification_status != DERIVATION_VERIFICATION_PENDING:
        raise ValueError("verification_already_recorded")
    if not verified:
        return replace(candidate, verification_status="FAILED")
    return replace(
        candidate,
        verification_status=DERIVATION_VERIFIED,
        persistence_status=DERIVATION_PERSISTENCE_ELIGIBLE,
    )


def assert_persistence_eligible(
    candidate: ArchitecturalDerivationCandidate,
) -> None:
    if candidate.falsification_status != DERIVATION_FALSIFICATION_SURVIVED:
        raise ValueError("persistence_requires_survived_falsification")
    if candidate.verification_status != DERIVATION_VERIFIED:
        raise ValueError("persistence_requires_verification")
    if candidate.persistence_status != DERIVATION_PERSISTENCE_ELIGIBLE:
        raise ValueError("derivation_not_persistence_eligible")
    if candidate.authority_effect != "NONE":
        raise ValueError("derivation_must_not_create_authority")
    if candidate.canon_effect != "NONE":
        raise ValueError("derivation_must_not_create_canon")
