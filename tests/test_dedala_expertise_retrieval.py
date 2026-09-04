import pytest

from app.expertise.registry import build_retrieval_plan
from app.expertise.retriever import retrieve_expert_evidence
from app.expertise.sources import (
    ExpertEvidenceFragment,
    ExpertSourceRecord,
    sha256_text,
)


def source(source_id: str, author: str, tags: tuple[str, ...]) -> ExpertSourceRecord:
    return ExpertSourceRecord(
        source_id=source_id,
        author=author,
        work="registered-work",
        edition_or_date="registered-edition",
        source_type="BOOK_OR_ARTICLE",
        locator="registered-locator",
        content_hash="0" * 64,
        ingestion_version="v1",
        licensing_access_class="METADATA_AND_AUTHORIZED_FRAGMENT_ONLY",
        retrieval_tags=tags,
    )


def fragment(
    source_id: str,
    fragment_id: str,
    content: str,
    tags: tuple[str, ...],
) -> ExpertEvidenceFragment:
    return ExpertEvidenceFragment(
        source_id=source_id,
        fragment_id=fragment_id,
        content=content,
        locator="chapter-or-section",
        content_hash=sha256_text(content),
        retrieval_tags=tags,
    )


def test_selective_retrieval_returns_provenance_bound_evidence() -> None:
    plan = build_retrieval_plan("distributed state consistency recovery message retry")
    sources = (
        source(
            "kleppmann-001",
            "Martin Kleppmann",
            ("distributed", "state", "consistency", "recovery"),
        ),
        source("hohpe-001", "Gregor Hohpe", ("message", "retry", "routing")),
        source("fowler-001", "Martin Fowler", ("refactoring", "architecture")),
    )
    fragments = (
        fragment(
            "kleppmann-001",
            "k-1",
            "Authorized local note about state recovery.",
            ("state", "recovery"),
        ),
        fragment(
            "hohpe-001",
            "h-1",
            "Authorized local note about message retry.",
            ("message", "retry"),
        ),
        fragment(
            "fowler-001",
            "f-1",
            "Authorized local note about refactoring.",
            ("refactoring",),
        ),
    )
    result = retrieve_expert_evidence(plan, sources, fragments)
    assert {item.source_id for item in result} == {"kleppmann-001", "hohpe-001"}
    assert all(item.authority_effect == "NONE" for item in result)
    assert all(item.canon_effect == "NONE" for item in result)


def test_corrupted_fragment_fails_closed() -> None:
    plan = build_retrieval_plan("distributed state consistency")
    sources = (
        source(
            "kleppmann-001",
            "Martin Kleppmann",
            ("distributed", "state", "consistency"),
        ),
    )
    bad = ExpertEvidenceFragment(
        source_id="kleppmann-001",
        fragment_id="k-bad",
        content="tampered",
        locator="section",
        content_hash="0" * 64,
        retrieval_tags=("state",),
    )
    with pytest.raises(ValueError, match="expert_fragment_integrity_failure"):
        retrieve_expert_evidence(plan, sources, (bad,))


def test_fragment_without_registered_source_fails_closed() -> None:
    plan = build_retrieval_plan("message retry")
    orphan = fragment("unknown", "x-1", "orphan evidence", ("message", "retry"))
    with pytest.raises(ValueError, match="expert_fragment_source_missing"):
        retrieve_expert_evidence(plan, (), (orphan,))


def test_unmatched_problem_retrieves_nothing() -> None:
    plan = build_retrieval_plan("unrelated lexical material")
    assert retrieve_expert_evidence(plan, (), ()) == ()
