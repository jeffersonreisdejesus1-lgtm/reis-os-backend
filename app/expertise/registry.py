from __future__ import annotations

from dataclasses import dataclass

EXPERT_SOURCE_CLASS = "RETRIEVABLE_EXTERNAL_TECHNICAL_SOURCE"
LOCAL_DERIVATION_INITIAL_STATUS = "LOCAL_ARCHITECTURAL_DERIVATION_CANDIDATE"
AUTHORITY_EFFECT_NONE = "NONE"


@dataclass(frozen=True)
class ExpertLens:
    lens_id: str
    source_family: str
    domains: tuple[str, ...]
    retrieval_tags: tuple[str, ...]
    source_class: str = EXPERT_SOURCE_CLASS


@dataclass(frozen=True)
class ExpertiseManifest:
    ocs_id: str
    capability_status: str
    lenses: tuple[ExpertLens, ...]
    identity_effect: str = "NONE"
    authority_effect: str = AUTHORITY_EFFECT_NONE
    canon_effect: str = "NONE"


@dataclass(frozen=True)
class RetrievalPlan:
    ocs_id: str
    problem: str
    candidate_lenses: tuple[str, ...]
    allowed_source_families: tuple[str, ...]
    retrieval_queries: tuple[str, ...]
    source_class: str
    derivation_status: str
    authority_effect: str


DEDALA_EXPERTISE_MANIFEST = ExpertiseManifest(
    ocs_id="DÉDALA",
    capability_status="OPTIONAL_SPECIALTY_CAPABILITY",
    lenses=(
        ExpertLens(
            lens_id="ARCH_REFACTORING_EVOLUTION",
            source_family="FOWLER",
            domains=("architecture", "refactoring", "evolution", "patterns"),
            retrieval_tags=(
                "refactor",
                "refactoring",
                "architecture",
                "evolution",
                "legacy",
                "pattern",
                "modularity",
            ),
        ),
        ExpertLens(
            lens_id="DATA_CONSISTENCY_CAUSALITY",
            source_family="KLEPPMANN",
            domains=(
                "distributed_state",
                "consistency",
                "causality",
                "recovery",
                "replication",
                "logs",
            ),
            retrieval_tags=(
                "state",
                "consistency",
                "causality",
                "recovery",
                "replication",
                "distributed",
                "log",
                "failure",
            ),
        ),
        ExpertLens(
            lens_id="BOUNDARY_DECOMPOSITION_COUPLING",
            source_family="NEWMAN",
            domains=(
                "boundaries",
                "decomposition",
                "coupling",
                "services",
                "migration",
            ),
            retrieval_tags=(
                "boundary",
                "boundaries",
                "decomposition",
                "coupling",
                "service",
                "microservice",
                "migration",
                "monolith",
            ),
        ),
        ExpertLens(
            lens_id="MESSAGE_INTEGRATION_ROUTING",
            source_family="HOHPE",
            domains=(
                "messaging",
                "integration",
                "events",
                "routing",
                "transformation",
            ),
            retrieval_tags=(
                "message",
                "messaging",
                "integration",
                "event",
                "routing",
                "handoff",
                "receipt",
                "retry",
                "delivery",
            ),
        ),
    ),
)


def validate_manifest(manifest: ExpertiseManifest) -> None:
    if manifest.ocs_id != "DÉDALA":
        raise ValueError("dedala_first_implementation_only")
    if manifest.identity_effect != "NONE":
        raise ValueError("expertise_must_not_change_identity")
    if manifest.authority_effect != AUTHORITY_EFFECT_NONE:
        raise ValueError("expertise_must_not_create_authority")
    if manifest.canon_effect != "NONE":
        raise ValueError("expertise_must_not_create_canon")
    if not manifest.lenses:
        raise ValueError("expertise_manifest_requires_lenses")
    if len({lens.lens_id for lens in manifest.lenses}) != len(manifest.lenses):
        raise ValueError("expert_lens_ids_must_be_unique")
    for lens in manifest.lenses:
        if lens.source_class != EXPERT_SOURCE_CLASS:
            raise ValueError("expert_source_must_remain_external_technical_source")
        if not lens.source_family.strip():
            raise ValueError("expert_lens_requires_source_family")
        if not lens.retrieval_tags:
            raise ValueError("expert_lens_requires_retrieval_tags")


def build_retrieval_plan(
    problem: str,
    manifest: ExpertiseManifest = DEDALA_EXPERTISE_MANIFEST,
) -> RetrievalPlan:
    validate_manifest(manifest)
    normalized = problem.casefold()
    scored: list[tuple[int, ExpertLens]] = []
    for lens in manifest.lenses:
        score = sum(1 for tag in lens.retrieval_tags if tag.casefold() in normalized)
        if score:
            scored.append((score, lens))
    scored.sort(key=lambda item: (-item[0], item[1].lens_id))
    selected = tuple(lens for _, lens in scored)
    candidate_lenses = tuple(lens.lens_id for lens in selected)
    allowed_source_families = tuple(dict.fromkeys(lens.source_family for lens in selected))
    retrieval_queries = tuple(
        f"{problem} :: {lens.lens_id} :: {','.join(lens.domains)}"
        for lens in selected
    )
    return RetrievalPlan(
        ocs_id=manifest.ocs_id,
        problem=problem,
        candidate_lenses=candidate_lenses,
        allowed_source_families=allowed_source_families,
        retrieval_queries=retrieval_queries,
        source_class=EXPERT_SOURCE_CLASS,
        derivation_status=LOCAL_DERIVATION_INITIAL_STATUS,
        authority_effect=AUTHORITY_EFFECT_NONE,
    )
