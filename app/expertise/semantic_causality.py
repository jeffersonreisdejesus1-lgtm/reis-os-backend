from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from .retriever import RetrievedExpertEvidence

SEMANTIC_CAUSALITY_SCOPE = "BOUNDED_COUNTERFACTUAL_HARNESS_ONLY"
QUALITY_EFFECT_SCOPE = "PREDECLARED_BOUNDED_RUBRIC_ONLY"


@dataclass(frozen=True)
class SemanticArchitectureRubric:
    rubric_id: str
    required_principles: tuple[str, ...]
    minimum_full_score: float = 1.0


@dataclass(frozen=True)
class SemanticArchitectureDecision:
    problem: str
    principles: tuple[str, ...]
    recommendation: str
    evidence_refs: tuple[str, ...]
    semantic_signature: str
    rubric_id: str
    quality_score: float
    status: str


@dataclass(frozen=True)
class CounterfactualSemanticReceipt:
    case_id: str
    full_signature: str
    ablated_signature: str
    substituted_signature: str | None
    full_quality_score: float
    ablated_quality_score: float
    substituted_quality_score: float | None
    semantic_derivation_causality_proven: bool
    bounded_quality_effect_proven: bool
    semantic_causality_scope: str = SEMANTIC_CAUSALITY_SCOPE
    quality_effect_scope: str = QUALITY_EFFECT_SCOPE
    reason: str = ""
    identity_effect: str = "NONE"
    authority_effect: str = "NONE"
    canon_effect: str = "NONE"


_PRINCIPLE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "INCREMENTAL_BEHAVIOR_PRESERVING_CHANGE",
        ("behavior-preserving", "all-at-once rewrite"),
    ),
    (
        "CONTINUOUS_TEST_SUPPORTED_REFACTORING",
        ("ongoing design activity", "supported by tests"),
    ),
    (
        "STALE_ACTOR_REJECTION_AT_PROTECTED_BOUNDARY",
        ("reject stale actors", "protected resource"),
    ),
    (
        "EXACT_FAILURE_SEMANTICS_OVER_COARSE_LABELS",
        ("exact operation", "failure mode"),
    ),
    (
        "BOUNDARY_BY_INFORMATION_HIDING_AND_COUPLING",
        ("information hiding", "coupling", "cohesion"),
    ),
    (
        "INCREMENTAL_GOAL_DRIVEN_DECOMPOSITION",
        ("decomposition", "incremental", "goal-driven"),
    ),
    (
        "EXPLICIT_ROUTING_BOUNDARY",
        ("routing responsibilities", "intermediary components"),
    ),
    (
        "EXPLICIT_TRANSFORMATION_BOUNDARY",
        ("transformation components", "format conversion"),
    ),
    (
        "EXPLICIT_MESSAGING_ENDPOINT_BOUNDARY",
        ("messaging endpoints", "explicit boundary"),
    ),
)

_RECOMMENDATION_CLAUSES = {
    "INCREMENTAL_BEHAVIOR_PRESERVING_CHANGE": (
        "evolve structure through small behavior-preserving changes"
    ),
    "CONTINUOUS_TEST_SUPPORTED_REFACTORING": (
        "treat refactoring as continuous design backed by tests"
    ),
    "STALE_ACTOR_REJECTION_AT_PROTECTED_BOUNDARY": (
        "reject stale actors at the protected resource boundary"
    ),
    "EXACT_FAILURE_SEMANTICS_OVER_COARSE_LABELS": (
        "model exact operations, guarantees, and failure semantics"
    ),
    "BOUNDARY_BY_INFORMATION_HIDING_AND_COUPLING": (
        "choose boundaries by information hiding, coupling, and cohesion"
    ),
    "INCREMENTAL_GOAL_DRIVEN_DECOMPOSITION": (
        "decompose incrementally against an explicit architectural goal"
    ),
    "EXPLICIT_ROUTING_BOUNDARY": (
        "isolate routing responsibility behind an explicit intermediary"
    ),
    "EXPLICIT_TRANSFORMATION_BOUNDARY": (
        "isolate representation conversion in explicit transformation components"
    ),
    "EXPLICIT_MESSAGING_ENDPOINT_BOUNDARY": (
        "keep messaging concerns behind explicit application endpoints"
    ),
}


def _evidence_ref(item: RetrievedExpertEvidence) -> str:
    return f"{item.source_id}:{item.fragment_id}@{item.locator}"


def extract_semantic_principles(
    evidence: tuple[RetrievedExpertEvidence, ...],
) -> tuple[str, ...]:
    material = " ".join(item.content.casefold() for item in evidence)
    principles = tuple(
        principle
        for principle, required_phrases in _PRINCIPLE_PATTERNS
        if all(phrase in material for phrase in required_phrases)
    )
    return principles


def _quality_score(
    principles: tuple[str, ...],
    rubric: SemanticArchitectureRubric,
) -> float:
    if not rubric.required_principles:
        raise ValueError("semantic_rubric_requires_principles")
    present = set(principles)
    hits = sum(1 for principle in rubric.required_principles if principle in present)
    return hits / len(rubric.required_principles)


def _semantic_signature(
    problem: str,
    principles: tuple[str, ...],
    recommendation: str,
) -> str:
    payload = dumps(
        {
            "problem": problem.strip(),
            "principles": principles,
            "recommendation": recommendation,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(payload).hexdigest()


def derive_semantic_architecture(
    *,
    problem: str,
    evidence: tuple[RetrievedExpertEvidence, ...],
    rubric: SemanticArchitectureRubric,
) -> SemanticArchitectureDecision:
    if not problem.strip():
        raise ValueError("semantic_derivation_requires_problem")
    principles = extract_semantic_principles(evidence)
    clauses = tuple(
        _RECOMMENDATION_CLAUSES[principle]
        for principle in principles
        if principle in _RECOMMENDATION_CLAUSES
    )
    recommendation = "; ".join(clauses)
    status = "SEMANTIC_DERIVATION_AVAILABLE" if clauses else "NO_SEMANTIC_DERIVATION"
    refs = tuple(dict.fromkeys(_evidence_ref(item) for item in evidence))
    return SemanticArchitectureDecision(
        problem=problem.strip(),
        principles=principles,
        recommendation=recommendation,
        evidence_refs=refs,
        semantic_signature=_semantic_signature(problem, principles, recommendation),
        rubric_id=rubric.rubric_id,
        quality_score=_quality_score(principles, rubric),
        status=status,
    )


def evaluate_counterfactual_semantic_causality(
    *,
    case_id: str,
    full: SemanticArchitectureDecision,
    ablated: SemanticArchitectureDecision,
    substituted: SemanticArchitectureDecision | None = None,
    rubric: SemanticArchitectureRubric,
) -> CounterfactualSemanticReceipt:
    if not case_id.strip():
        raise ValueError("semantic_causality_case_id_required")
    if {full.rubric_id, ablated.rubric_id} != {rubric.rubric_id}:
        raise ValueError("semantic_causality_rubric_mismatch")
    if substituted is not None and substituted.rubric_id != rubric.rubric_id:
        raise ValueError("semantic_causality_rubric_mismatch")

    signature_changed = full.semantic_signature != ablated.semantic_signature
    substitution_changed = (
        True
        if substituted is None
        else full.semantic_signature != substituted.semantic_signature
    )
    semantic_proven = signature_changed and substitution_changed

    full_meets_rubric = full.quality_score >= rubric.minimum_full_score
    ablation_degrades = ablated.quality_score < full.quality_score
    substitution_degrades = (
        True
        if substituted is None
        else substituted.quality_score < full.quality_score
    )
    quality_proven = full_meets_rubric and ablation_degrades and substitution_degrades
    proven = semantic_proven and quality_proven

    return CounterfactualSemanticReceipt(
        case_id=case_id,
        full_signature=full.semantic_signature,
        ablated_signature=ablated.semantic_signature,
        substituted_signature=(
            None if substituted is None else substituted.semantic_signature
        ),
        full_quality_score=full.quality_score,
        ablated_quality_score=ablated.quality_score,
        substituted_quality_score=(
            None if substituted is None else substituted.quality_score
        ),
        semantic_derivation_causality_proven=semantic_proven,
        bounded_quality_effect_proven=quality_proven,
        reason=(
            "bounded_counterfactual_semantic_and_quality_effect_proven"
            if proven
            else "bounded_counterfactual_semantic_or_quality_effect_not_proven"
        ),
    )
