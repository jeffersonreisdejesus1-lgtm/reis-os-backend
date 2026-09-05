from __future__ import annotations

from dataclasses import dataclass

from app.expertise.corpus import DEDALA_EXPERT_FRAGMENTS, DEDALA_EXPERT_SOURCES
from app.expertise.registry import build_retrieval_plan
from app.expertise.retriever import RetrievedExpertEvidence, retrieve_expert_evidence
from app.expertise.semantic_causality import (
    QUALITY_EFFECT_SCOPE,
    SEMANTIC_CAUSALITY_SCOPE,
    SemanticArchitectureRubric,
    derive_semantic_architecture,
    evaluate_counterfactual_semantic_causality,
)


@dataclass(frozen=True)
class SemanticCase:
    case_id: str
    problem: str
    source_family: str
    rubric: SemanticArchitectureRubric
    substitute_problem: str


SEMANTIC_CASES = (
    SemanticCase(
        case_id="DEDALA-SEMANTIC-FOWLER-001",
        problem=(
            "legacy architecture refactoring evolution with incremental structural "
            "change and tests"
        ),
        source_family="FOWLER",
        rubric=SemanticArchitectureRubric(
            rubric_id="RUBRIC-FOWLER-001",
            required_principles=(
                "INCREMENTAL_BEHAVIOR_PRESERVING_CHANGE",
                "CONTINUOUS_TEST_SUPPORTED_REFACTORING",
            ),
        ),
        substitute_problem=(
            "distributed state consistency failure recovery stale writer protection"
        ),
    ),
    SemanticCase(
        case_id="DEDALA-SEMANTIC-KLEPPMANN-001",
        problem=(
            "distributed state consistency failure recovery stale writer protection"
        ),
        source_family="KLEPPMANN",
        rubric=SemanticArchitectureRubric(
            rubric_id="RUBRIC-KLEPPMANN-001",
            required_principles=(
                "STALE_ACTOR_REJECTION_AT_PROTECTED_BOUNDARY",
                "EXACT_FAILURE_SEMANTICS_OVER_COARSE_LABELS",
            ),
        ),
        substitute_problem=(
            "service boundary decomposition coupling migration from a monolith"
        ),
    ),
    SemanticCase(
        case_id="DEDALA-SEMANTIC-NEWMAN-001",
        problem="service boundary decomposition coupling migration from a monolith",
        source_family="NEWMAN",
        rubric=SemanticArchitectureRubric(
            rubric_id="RUBRIC-NEWMAN-001",
            required_principles=(
                "BOUNDARY_BY_INFORMATION_HIDING_AND_COUPLING",
                "INCREMENTAL_GOAL_DRIVEN_DECOMPOSITION",
            ),
        ),
        substitute_problem=(
            "message integration routing transformation delivery across boundaries"
        ),
    ),
    SemanticCase(
        case_id="DEDALA-SEMANTIC-HOHPE-001",
        problem=(
            "message integration routing transformation delivery across system "
            "boundaries"
        ),
        source_family="HOHPE",
        rubric=SemanticArchitectureRubric(
            rubric_id="RUBRIC-HOHPE-001",
            required_principles=(
                "EXPLICIT_ROUTING_BOUNDARY",
                "EXPLICIT_TRANSFORMATION_BOUNDARY",
                "EXPLICIT_MESSAGING_ENDPOINT_BOUNDARY",
            ),
        ),
        substitute_problem=(
            "legacy architecture refactoring evolution incremental change and tests"
        ),
    ),
)


def _retrieve(
    problem: str,
    *,
    exclude_family: str | None = None,
) -> tuple[RetrievedExpertEvidence, ...]:
    plan = build_retrieval_plan(problem)
    sources = tuple(
        source
        for source in DEDALA_EXPERT_SOURCES
        if source.source_family != exclude_family
    )
    source_ids = {source.source_id for source in sources}
    fragments = tuple(
        fragment
        for fragment in DEDALA_EXPERT_FRAGMENTS
        if fragment.source_id in source_ids
    )
    return retrieve_expert_evidence(plan, sources, fragments)


def test_external_knowledge_changes_architectural_form_counterfactually() -> None:
    for case in SEMANTIC_CASES:
        full_evidence = _retrieve(case.problem)
        ablated_evidence = _retrieve(case.problem, exclude_family=case.source_family)
        substituted_evidence = _retrieve(case.substitute_problem)

        full = derive_semantic_architecture(
            problem=case.problem,
            evidence=full_evidence,
            rubric=case.rubric,
        )
        ablated = derive_semantic_architecture(
            problem=case.problem,
            evidence=ablated_evidence,
            rubric=case.rubric,
        )
        substituted = derive_semantic_architecture(
            problem=case.problem,
            evidence=substituted_evidence,
            rubric=case.rubric,
        )
        receipt = evaluate_counterfactual_semantic_causality(
            case_id=case.case_id,
            full=full,
            ablated=ablated,
            substituted=substituted,
            rubric=case.rubric,
        )

        assert full.status == "SEMANTIC_DERIVATION_AVAILABLE"
        assert full.quality_score == 1.0
        assert ablated.quality_score < full.quality_score
        assert substituted.quality_score < full.quality_score
        assert full.semantic_signature != ablated.semantic_signature
        assert full.semantic_signature != substituted.semantic_signature
        assert receipt.semantic_derivation_causality_proven is True
        assert receipt.bounded_quality_effect_proven is True
        assert receipt.reason == (
            "bounded_counterfactual_semantic_and_quality_effect_proven"
        )
        assert receipt.semantic_causality_scope == SEMANTIC_CAUSALITY_SCOPE
        assert receipt.quality_effect_scope == QUALITY_EFFECT_SCOPE
        assert receipt.identity_effect == "NONE"
        assert receipt.authority_effect == "NONE"
        assert receipt.canon_effect == "NONE"


def test_ablated_family_cannot_recreate_required_semantic_principles() -> None:
    for case in SEMANTIC_CASES:
        full = derive_semantic_architecture(
            problem=case.problem,
            evidence=_retrieve(case.problem),
            rubric=case.rubric,
        )
        ablated = derive_semantic_architecture(
            problem=case.problem,
            evidence=_retrieve(case.problem, exclude_family=case.source_family),
            rubric=case.rubric,
        )
        required = set(case.rubric.required_principles)
        assert required.issubset(set(full.principles))
        assert not required.issubset(set(ablated.principles))


def test_quality_claim_is_explicitly_bounded_to_predeclared_rubric() -> None:
    case = SEMANTIC_CASES[0]
    decision = derive_semantic_architecture(
        problem=case.problem,
        evidence=_retrieve(case.problem),
        rubric=case.rubric,
    )
    assert decision.quality_score == 1.0
    assert QUALITY_EFFECT_SCOPE == "PREDECLARED_BOUNDED_RUBRIC_ONLY"
    assert SEMANTIC_CAUSALITY_SCOPE == "BOUNDED_COUNTERFACTUAL_HARNESS_ONLY"
