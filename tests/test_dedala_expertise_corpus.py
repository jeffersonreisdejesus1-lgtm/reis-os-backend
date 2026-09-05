from __future__ import annotations

from app.expertise.corpus import (
    CORPUS_ACCESS_CLASS,
    DEDALA_EXPERT_FRAGMENTS,
    DEDALA_EXPERT_SOURCES,
    validate_seed_corpus,
)
from app.expertise.registry import build_retrieval_plan
from app.expertise.retriever import retrieve_expert_evidence
from app.expertise.sources import validate_fragment, validate_source_record


def test_seed_corpus_has_all_four_source_families_and_valid_integrity() -> None:
    validate_seed_corpus()
    for source in DEDALA_EXPERT_SOURCES:
        validate_source_record(source)
        assert source.licensing_access_class == CORPUS_ACCESS_CLASS
        assert source.source_class == "RETRIEVABLE_EXTERNAL_TECHNICAL_SOURCE"
    for fragment in DEDALA_EXPERT_FRAGMENTS:
        validate_fragment(fragment)

    prefixes = {source.source_id.split("-", 1)[0] for source in DEDALA_EXPERT_SOURCES}
    assert {"FOWLER", "KLEPPMANN", "NEWMAN", "HOHPE"}.issubset(prefixes)


def test_fowler_problem_retrieves_refactoring_evidence_without_authority_effect() -> None:
    plan = build_retrieval_plan("legacy architecture refactoring evolution")
    evidence = retrieve_expert_evidence(plan, DEDALA_EXPERT_SOURCES, DEDALA_EXPERT_FRAGMENTS)
    assert any(item.source_id.startswith("FOWLER-") for item in evidence)
    assert all(item.authority_effect == "NONE" for item in evidence)
    assert all(item.canon_effect == "NONE" for item in evidence)


def test_kleppmann_problem_retrieves_distributed_consistency_evidence() -> None:
    plan = build_retrieval_plan("distributed consistency failure state")
    evidence = retrieve_expert_evidence(plan, DEDALA_EXPERT_SOURCES, DEDALA_EXPERT_FRAGMENTS)
    assert any(item.source_id.startswith("KLEPPMANN-") for item in evidence)


def test_newman_problem_retrieves_boundary_and_coupling_evidence() -> None:
    plan = build_retrieval_plan("service boundary decomposition coupling")
    evidence = retrieve_expert_evidence(plan, DEDALA_EXPERT_SOURCES, DEDALA_EXPERT_FRAGMENTS)
    assert any(item.source_id.startswith("NEWMAN-") for item in evidence)


def test_hohpe_problem_retrieves_messaging_routing_evidence() -> None:
    plan = build_retrieval_plan("message integration routing delivery")
    evidence = retrieve_expert_evidence(plan, DEDALA_EXPERT_SOURCES, DEDALA_EXPERT_FRAGMENTS)
    assert any(item.source_id.startswith("HOHPE-") for item in evidence)


def test_corpus_is_bounded_original_paraphrase_not_claimed_as_canon() -> None:
    assert len(DEDALA_EXPERT_SOURCES) == 10
    assert len(DEDALA_EXPERT_FRAGMENTS) == 12
    assert all(
        source.source_type == "PUBLIC_WEB_REFERENCE_WITH_ORIGINAL_PARAPHRASE"
        for source in DEDALA_EXPERT_SOURCES
    )
    assert all("canon" not in fragment.content.casefold() for fragment in DEDALA_EXPERT_FRAGMENTS)
