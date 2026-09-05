from __future__ import annotations

# ruff: noqa: E501
from .sources import ExpertEvidenceFragment, ExpertSourceRecord, sha256_text

CORPUS_INGESTION_VERSION = "dedala-expertise-corpus-v0.1.0"
CORPUS_ACCESS_CLASS = "PUBLIC_REFERENCE_ORIGINAL_PARAPHRASE_ONLY"
SOURCE_TYPE = "PUBLIC_WEB_REFERENCE_WITH_ORIGINAL_PARAPHRASE"


def _source(
    *,
    source_id: str,
    author: str,
    work: str,
    edition_or_date: str,
    locator: str,
    retrieval_tags: tuple[str, ...],
) -> ExpertSourceRecord:
    source_capsule = "|".join(
        (
            source_id,
            author,
            work,
            edition_or_date,
            locator,
            CORPUS_INGESTION_VERSION,
            CORPUS_ACCESS_CLASS,
        )
    )
    return ExpertSourceRecord(
        source_id=source_id,
        author=author,
        work=work,
        edition_or_date=edition_or_date,
        source_type=SOURCE_TYPE,
        locator=locator,
        content_hash=sha256_text(source_capsule),
        ingestion_version=CORPUS_INGESTION_VERSION,
        licensing_access_class=CORPUS_ACCESS_CLASS,
        retrieval_tags=retrieval_tags,
    )


def _fragment(
    *,
    source_id: str,
    fragment_id: str,
    content: str,
    locator: str,
    retrieval_tags: tuple[str, ...],
) -> ExpertEvidenceFragment:
    return ExpertEvidenceFragment(
        source_id=source_id,
        fragment_id=fragment_id,
        content=content,
        locator=locator,
        content_hash=sha256_text(content),
        retrieval_tags=retrieval_tags,
    )


DEDALA_EXPERT_SOURCES = (
    _source(
        source_id="FOWLER-REFACTORING-2018",
        author="Martin Fowler",
        work="Refactoring: Improving the Design of Existing Code",
        edition_or_date="2nd edition, 2018",
        locator="https://martinfowler.com/books/refactoring.html",
        retrieval_tags=("refactor", "refactoring", "evolution", "legacy", "testing"),
    ),
    _source(
        source_id="FOWLER-POEAA-2002",
        author="Martin Fowler",
        work="Patterns of Enterprise Application Architecture",
        edition_or_date="2002",
        locator="https://martinfowler.com/books/eaa.html",
        retrieval_tags=("architecture", "pattern", "modularity", "enterprise"),
    ),
    _source(
        source_id="KLEPPMANN-DISTRIBUTED-LOCKING-2016",
        author="Martin Kleppmann",
        work="How to do distributed locking",
        edition_or_date="2016-02-08",
        locator="https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html",
        retrieval_tags=("distributed", "consistency", "failure", "state", "locking"),
    ),
    _source(
        source_id="KLEPPMANN-CAP-2015",
        author="Martin Kleppmann",
        work="Please stop calling databases CP or AP",
        edition_or_date="2015-05-11",
        locator="https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html",
        retrieval_tags=("distributed", "consistency", "failure", "replication", "database"),
    ),
    _source(
        source_id="KLEPPMANN-KAFKA-TOPICS-2018",
        author="Martin Kleppmann",
        work="Should you put several event types in the same Kafka topic?",
        edition_or_date="2018-01-18",
        locator="https://martin.kleppmann.com/2018/01/18/event-types-in-kafka-topic.html",
        retrieval_tags=("event", "log", "distributed", "stream", "topic"),
    ),
    _source(
        source_id="NEWMAN-BUILDING-MICROSERVICES-2E",
        author="Sam Newman",
        work="Building Microservices, 2nd Edition",
        edition_or_date="2nd edition",
        locator="https://samnewman.io/books/building_microservices_2nd_edition/",
        retrieval_tags=("boundary", "coupling", "service", "microservice", "decomposition"),
    ),
    _source(
        source_id="NEWMAN-COUPLING-COHESION",
        author="Sam Newman",
        work="Hiding The Lead: Information hiding, coupling, and cohesion",
        edition_or_date="public talk page",
        locator="https://samnewman.io/talks/microservices-coupling-cohesion/",
        retrieval_tags=("boundary", "coupling", "service", "microservice", "cohesion"),
    ),
    _source(
        source_id="NEWMAN-GREENFIELD-2015",
        author="Sam Newman",
        work="Microservices For Greenfield?",
        edition_or_date="2015-04-07",
        locator="https://samnewman.io/blog/2015/04/07/microservices-for-greenfield/",
        retrieval_tags=("boundary", "decomposition", "coupling", "migration", "monolith"),
    ),
    _source(
        source_id="HOHPE-EIP-INTRODUCTION",
        author="Gregor Hohpe",
        work="Enterprise Integration Patterns: Introduction",
        edition_or_date="public pattern site",
        locator="https://www.enterpriseintegrationpatterns.com/patterns/messaging/Introduction.html",
        retrieval_tags=("message", "messaging", "integration", "routing", "transformation"),
    ),
    _source(
        source_id="HOHPE-EIP-MESSAGING-OVERVIEW",
        author="Gregor Hohpe",
        work="Messaging Patterns Overview",
        edition_or_date="public pattern site",
        locator="https://www.enterpriseintegrationpatterns.com/patterns/messaging/index.html",
        retrieval_tags=("message", "messaging", "integration", "routing", "event", "delivery"),
    ),
)


DEDALA_EXPERT_FRAGMENTS = (
    _fragment(
        source_id="FOWLER-REFACTORING-2018",
        fragment_id="FOWLER-REF-001",
        content="Prefer small, behavior-preserving structural changes so architecture can evolve without requiring a risky all-at-once rewrite.",
        locator="https://martinfowler.com/books/refactoring.html",
        retrieval_tags=("refactor", "refactoring", "evolution", "legacy"),
    ),
    _fragment(
        source_id="FOWLER-REFACTORING-2018",
        fragment_id="FOWLER-REF-002",
        content="Treat refactoring as an ongoing design activity supported by tests, not as a separate rewrite phase performed only after deterioration.",
        locator="https://martinfowler.com/books/refactoring.html",
        retrieval_tags=("refactoring", "testing", "evolution", "architecture"),
    ),
    _fragment(
        source_id="FOWLER-POEAA-2002",
        fragment_id="FOWLER-ARCH-001",
        content="Enterprise architecture patterns are reusable descriptions of recurring design structures; their value depends on matching a pattern to the forces of the current context.",
        locator="https://martinfowler.com/books/eaa.html",
        retrieval_tags=("architecture", "pattern", "enterprise", "modularity"),
    ),
    _fragment(
        source_id="KLEPPMANN-DISTRIBUTED-LOCKING-2016",
        fragment_id="KLEPPMANN-LOCK-001",
        content="When a distributed lock protects correctness rather than merely efficiency, the protected resource must reject stale actors; fencing tokens are one way to enforce that boundary.",
        locator="https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html",
        retrieval_tags=("distributed", "consistency", "failure", "state", "locking"),
    ),
    _fragment(
        source_id="KLEPPMANN-CAP-2015",
        fragment_id="KLEPPMANN-CAP-001",
        content="Avoid reducing a distributed datastore to a simple CP or AP label; reason about the exact operation, guarantees, failure mode, and configuration instead.",
        locator="https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html",
        retrieval_tags=("distributed", "consistency", "failure", "database"),
    ),
    _fragment(
        source_id="KLEPPMANN-KAFKA-TOPICS-2018",
        fragment_id="KLEPPMANN-KAFKA-001",
        content="Event-stream partitioning should balance consumer selectivity against operational overhead; neither one universal topic nor extreme topic fragmentation is a sound default.",
        locator="https://martin.kleppmann.com/2018/01/18/event-types-in-kafka-topic.html",
        retrieval_tags=("event", "log", "distributed", "stream"),
    ),
    _fragment(
        source_id="NEWMAN-COUPLING-COHESION",
        fragment_id="NEWMAN-BOUND-001",
        content="Service boundaries should follow information hiding, coupling, cohesion, and domain understanding rather than arbitrary technical layers.",
        locator="https://samnewman.io/talks/microservices-coupling-cohesion/",
        retrieval_tags=("boundary", "coupling", "service", "microservice"),
    ),
    _fragment(
        source_id="NEWMAN-GREENFIELD-2015",
        fragment_id="NEWMAN-DECOMP-001",
        content="Decomposition should be incremental and goal-driven because incorrect service boundaries create expensive cross-service change and coupling.",
        locator="https://samnewman.io/blog/2015/04/07/microservices-for-greenfield/",
        retrieval_tags=("decomposition", "boundary", "coupling", "migration", "monolith"),
    ),
    _fragment(
        source_id="NEWMAN-BUILDING-MICROSERVICES-2E",
        fragment_id="NEWMAN-COMM-001",
        content="Choose synchronous, asynchronous, request-response, or event-driven collaboration according to workflow and coupling consequences rather than adopting one communication style universally.",
        locator="https://samnewman.io/books/building_microservices_2nd_edition/",
        retrieval_tags=("service", "microservice", "coupling", "event", "workflow"),
    ),
    _fragment(
        source_id="HOHPE-EIP-INTRODUCTION",
        fragment_id="HOHPE-ROUTE-001",
        content="As messaging topologies grow, senders should not need detailed receiver knowledge; routing responsibilities can be isolated in explicit intermediary components.",
        locator="https://www.enterpriseintegrationpatterns.com/patterns/messaging/Introduction.html",
        retrieval_tags=("message", "messaging", "integration", "routing"),
    ),
    _fragment(
        source_id="HOHPE-EIP-INTRODUCTION",
        fragment_id="HOHPE-TRANSFORM-001",
        content="When independently evolved systems disagree on message representation or meaning, explicit transformation components should mediate the contract instead of leaking format conversion everywhere.",
        locator="https://www.enterpriseintegrationpatterns.com/patterns/messaging/Introduction.html",
        retrieval_tags=("message", "integration", "transformation", "contract"),
    ),
    _fragment(
        source_id="HOHPE-EIP-MESSAGING-OVERVIEW",
        fragment_id="HOHPE-ENDPOINT-001",
        content="Messaging endpoints form an explicit boundary between an application and the messaging infrastructure, keeping message production and consumption concerns from diffusing through domain code.",
        locator="https://www.enterpriseintegrationpatterns.com/patterns/messaging/index.html",
        retrieval_tags=("message", "messaging", "integration", "boundary", "delivery"),
    ),
)


def validate_seed_corpus() -> None:
    source_ids = {source.source_id for source in DEDALA_EXPERT_SOURCES}
    if len(source_ids) != len(DEDALA_EXPERT_SOURCES):
        raise ValueError("expert_corpus_source_ids_must_be_unique")
    fragment_ids = {fragment.fragment_id for fragment in DEDALA_EXPERT_FRAGMENTS}
    if len(fragment_ids) != len(DEDALA_EXPERT_FRAGMENTS):
        raise ValueError("expert_corpus_fragment_ids_must_be_unique")
    if any(fragment.source_id not in source_ids for fragment in DEDALA_EXPERT_FRAGMENTS):
        raise ValueError("expert_corpus_fragment_source_missing")

    required_families = ("FOWLER-", "KLEPPMANN-", "NEWMAN-", "HOHPE-")
    for prefix in required_families:
        if not any(source.source_id.startswith(prefix) for source in DEDALA_EXPERT_SOURCES):
            raise ValueError("expert_corpus_family_missing")
        if not any(fragment.fragment_id.startswith(prefix) for fragment in DEDALA_EXPERT_FRAGMENTS):
            raise ValueError("expert_corpus_family_fragment_missing")
