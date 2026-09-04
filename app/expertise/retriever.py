from __future__ import annotations

from dataclasses import dataclass

from .registry import RetrievalPlan
from .sources import (
    ExpertEvidenceFragment,
    ExpertSourceRecord,
    validate_fragment,
    validate_source_record,
)


@dataclass(frozen=True)
class RetrievedExpertEvidence:
    source_id: str
    fragment_id: str
    locator: str
    content: str
    source_class: str
    applicability_score: int
    authority_effect: str = "NONE"
    canon_effect: str = "NONE"


def retrieve_expert_evidence(
    plan: RetrievalPlan,
    sources: tuple[ExpertSourceRecord, ...],
    fragments: tuple[ExpertEvidenceFragment, ...],
) -> tuple[RetrievedExpertEvidence, ...]:
    if plan.authority_effect != "NONE":
        raise ValueError("retrieval_must_not_expand_authority")
    if not plan.candidate_lenses:
        return ()

    source_by_id = {source.source_id: source for source in sources}
    for source in sources:
        validate_source_record(source)

    query_terms = set(plan.problem.casefold().split())
    evidence: list[RetrievedExpertEvidence] = []
    for fragment in fragments:
        validate_fragment(fragment)
        source = source_by_id.get(fragment.source_id)
        if source is None:
            raise ValueError("expert_fragment_source_missing")
        tags = {
            tag.casefold()
            for tag in source.retrieval_tags + fragment.retrieval_tags
        }
        score = len(query_terms.intersection(tags))
        if score == 0:
            continue
        evidence.append(
            RetrievedExpertEvidence(
                source_id=source.source_id,
                fragment_id=fragment.fragment_id,
                locator=fragment.locator,
                content=fragment.content,
                source_class=source.source_class,
                applicability_score=score,
            )
        )
    evidence.sort(
        key=lambda item: (
            -item.applicability_score,
            item.source_id,
            item.fragment_id,
        )
    )
    return tuple(evidence)
