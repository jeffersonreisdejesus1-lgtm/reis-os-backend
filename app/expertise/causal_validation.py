from __future__ import annotations

from dataclasses import dataclass

from .corpus import (
    DEDALA_EXPERT_FRAGMENTS,
    DEDALA_EXPERT_SOURCES,
    validate_seed_corpus,
)
from .derivation import draft_architectural_derivation
from .registry import build_retrieval_plan
from .retriever import retrieve_expert_evidence


@dataclass(frozen=True)
class RepresentativeArchitectureCase:
    case_id: str
    problem: str
    proposition: str
    expected_lens: str
    expected_source_family: str


@dataclass(frozen=True)
class CausalExpertiseReceipt:
    case_id: str
    selected_lenses: tuple[str, ...]
    source_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    causal_consumption_proven: bool
    reason: str
    semantic_derivation_causality_proven: bool = False
    identity_effect: str = "NONE"
    authority_effect: str = "NONE"
    canon_effect: str = "NONE"


REPRESENTATIVE_ARCHITECTURE_CASES = (
    RepresentativeArchitectureCase(
        case_id="DEDALA-CAUSAL-FOWLER-001",
        problem=(
            "legacy architecture refactoring evolution with incremental structural "
            "change"
        ),
        proposition=(
            "Prefer an incremental behavior-preserving refactoring sequence over a "
            "big-bang rewrite."
        ),
        expected_lens="ARCH_REFACTORING_EVOLUTION",
        expected_source_family="FOWLER",
    ),
    RepresentativeArchitectureCase(
        case_id="DEDALA-CAUSAL-KLEPPMANN-001",
        problem=(
            "distributed state consistency failure recovery and stale-writer "
            "protection"
        ),
        proposition=(
            "Require stale-writer rejection at the protected state boundary and "
            "reason about exact failure semantics."
        ),
        expected_lens="DATA_CONSISTENCY_CAUSALITY",
        expected_source_family="KLEPPMANN",
    ),
    RepresentativeArchitectureCase(
        case_id="DEDALA-CAUSAL-NEWMAN-001",
        problem=(
            "service boundary decomposition coupling migration from a monolith"
        ),
        proposition=(
            "Choose boundaries by information hiding and coupling, then decompose "
            "incrementally."
        ),
        expected_lens="BOUNDARY_DECOMPOSITION_COUPLING",
        expected_source_family="NEWMAN",
    ),
    RepresentativeArchitectureCase(
        case_id="DEDALA-CAUSAL-HOHPE-001",
        problem=(
            "message integration routing transformation delivery across system "
            "boundaries"
        ),
        proposition=(
            "Isolate routing and transformation responsibilities behind explicit "
            "messaging boundaries."
        ),
        expected_lens="MESSAGE_INTEGRATION_ROUTING",
        expected_source_family="HOHPE",
    ),
)


def evaluate_representative_case(
    case: RepresentativeArchitectureCase,
) -> CausalExpertiseReceipt:
    """Prove only bounded routing/evidence-attachment causality.

    The harness proves that the problem selects a lens, that the lens constrains the
    eligible source family, and that provenance-bound evidence from that family is
    attached to the local derivation candidate. It deliberately does NOT prove that
    the evidence semantically caused the proposition or that the proposition is
    architecturally superior.
    """

    validate_seed_corpus()
    plan = build_retrieval_plan(case.problem)
    evidence = retrieve_expert_evidence(
        plan,
        DEDALA_EXPERT_SOURCES,
        DEDALA_EXPERT_FRAGMENTS,
    )

    if case.expected_lens not in plan.candidate_lenses:
        return CausalExpertiseReceipt(
            case_id=case.case_id,
            selected_lenses=plan.candidate_lenses,
            source_ids=tuple(item.source_id for item in evidence),
            evidence_refs=(),
            causal_consumption_proven=False,
            reason="expected_lens_not_selected",
        )
    if case.expected_source_family not in plan.allowed_source_families:
        return CausalExpertiseReceipt(
            case_id=case.case_id,
            selected_lenses=plan.candidate_lenses,
            source_ids=tuple(item.source_id for item in evidence),
            evidence_refs=(),
            causal_consumption_proven=False,
            reason="expected_source_family_not_authorized_by_lens",
        )

    family_evidence = tuple(
        item for item in evidence if item.source_family == case.expected_source_family
    )
    if not family_evidence:
        return CausalExpertiseReceipt(
            case_id=case.case_id,
            selected_lenses=plan.candidate_lenses,
            source_ids=tuple(item.source_id for item in evidence),
            evidence_refs=(),
            causal_consumption_proven=False,
            reason="expected_source_family_not_retrieved",
        )

    candidate = draft_architectural_derivation(plan, evidence, case.proposition)
    source_ids = tuple(item.source_id for item in evidence)
    effects_preserved = (
        plan.authority_effect == "NONE"
        and candidate.identity_effect == "NONE"
        and candidate.authority_effect == "NONE"
        and candidate.canon_effect == "NONE"
        and all(item.authority_effect == "NONE" for item in evidence)
        and all(item.canon_effect == "NONE" for item in evidence)
    )
    evidence_grounded = bool(candidate.evidence_refs) and all(
        any(ref.startswith(f"{source_id}:") for source_id in source_ids)
        for ref in candidate.evidence_refs
    )
    proven = effects_preserved and evidence_grounded

    return CausalExpertiseReceipt(
        case_id=case.case_id,
        selected_lenses=plan.candidate_lenses,
        source_ids=source_ids,
        evidence_refs=candidate.evidence_refs,
        causal_consumption_proven=proven,
        reason=(
            "bounded_routing_and_evidence_attachment_causality_proven"
            if proven
            else "causal_chain_integrity_failed"
        ),
        semantic_derivation_causality_proven=False,
    )


def evaluate_representative_suite() -> tuple[CausalExpertiseReceipt, ...]:
    return tuple(
        evaluate_representative_case(case)
        for case in REPRESENTATIVE_ARCHITECTURE_CASES
    )
