# DEDALA-EXPERTISE-CORPUS-001

Status: bounded seeded corpus for Dédala expertise retrieval.

## Purpose

Materialize a small provenance-bound technical corpus for the four configured Dédala lenses without turning authors into identity, authority, empirical proof, or canon.

## Corpus policy

- Source records point to public technical references.
- Stored fragments are original paraphrases written for REIS OS retrieval; no book chapter, article body, or long quotation is copied into the repository.
- `PUBLIC_REFERENCE_ORIGINAL_PARAPHRASE_ONLY` means the repository stores reference metadata plus original paraphrases, not a mirrored copyrighted source corpus.
- Fragment hashes protect the stored paraphrase text.
- Source capsule hashes protect the local provenance capsule; they do not claim to be hashes of remote webpages.
- External references remain `RETRIEVABLE_EXTERNAL_TECHNICAL_SOURCE`.
- Retrieval produces no identity, authority, or canon effect.

## Source families

### FOWLER

- Refactoring: Improving the Design of Existing Code, 2nd edition (2018)
  - https://martinfowler.com/books/refactoring.html
- Patterns of Enterprise Application Architecture (2002)
  - https://martinfowler.com/books/eaa.html

Primary lens: `ARCH_REFACTORING_EVOLUTION`.

### KLEPPMANN

- How to do distributed locking (2016)
  - https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- Please stop calling databases CP or AP (2015)
  - https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html
- Should you put several event types in the same Kafka topic? (2018)
  - https://martin.kleppmann.com/2018/01/18/event-types-in-kafka-topic.html

Primary lens: `DATA_CONSISTENCY_CAUSALITY`.

### NEWMAN

- Building Microservices, 2nd Edition
  - https://samnewman.io/books/building_microservices_2nd_edition/
- Hiding The Lead: Information hiding, coupling, and cohesion
  - https://samnewman.io/talks/microservices-coupling-cohesion/
- Microservices For Greenfield? (2015)
  - https://samnewman.io/blog/2015/04/07/microservices-for-greenfield/

Primary lens: `BOUNDARY_DECOMPOSITION_COUPLING`.

### HOHPE

- Enterprise Integration Patterns: Introduction
  - https://www.enterpriseintegrationpatterns.com/patterns/messaging/Introduction.html
- Messaging Patterns Overview
  - https://www.enterpriseintegrationpatterns.com/patterns/messaging/index.html

Primary lens: `MESSAGE_INTEGRATION_ROUTING`.

## Bounded scope

`SOURCE_COUNT = 10`

`PARAPHRASE_FRAGMENT_COUNT = 12`

`EXTERNAL_EXPERT_CORPUS_MIRROR = FALSE`

`COPYRIGHTED_LONG_FORM_INGESTION = FALSE`

`IDENTITY_EFFECT = NONE`

`AUTHORITY_EFFECT = NONE`

`CANON_EFFECT = NONE`

This corpus is deliberately small. Expansion requires the same provenance, licensing/access, integrity, applicability, and epistemic boundaries.
