# DEDALA-EXPERTISE-LAYER-REFACTOR-001

STATUS = IMPLEMENTATION_CANDIDATE / FIRST_SLICE
FOUNDER_AUTHORITY = EXPLICIT_2026-09-04
FOUNDER_SCOPE = START_DEDALA_REFACTOR_FROM_EXPERTISE_REPORTS
FOUNDATIONAL_REOPENING = FALSE
TARGET_OCS = DÉDALA

## Purpose

Introduce persistent, selectable architectural expertise into Dédala without changing Dédala identity, authority, canon, or autobiographical memory.

## Architectural boundary

OCS_HAS_ACCESS_TO_EXPERTISE != OCS_IS_THE_EXPERT
RETRIEVAL != IDENTITY
SOURCE != AUTHORITY
DERIVATION != CANON
LEARNING != PROMOTION
EXPERT_SOURCE != EMPIRICAL_PROOF

## First implementation

EXPERTISE_REGISTRY = OPTIONAL_SPECIALTY_CAPABILITY
FIRST_IMPLEMENTATION = DÉDALA

The first manifest exposes technical lenses rather than expert personas:

- ARCH_REFACTORING_EVOLUTION / source family FOWLER
- DATA_CONSISTENCY_CAUSALITY / source family KLEPPMANN
- BOUNDARY_DECOMPOSITION_COUPLING / source family NEWMAN
- MESSAGE_INTEGRATION_ROUTING / source family HOHPE

The registry performs problem-based lens selection and emits retrieval plans. It does not ingest or reproduce copyrighted source corpora and does not infer authority from reputation.

## Epistemic states

EXPERT_SOURCE_CLASS = RETRIEVABLE_EXTERNAL_TECHNICAL_SOURCE
INITIAL_DERIVATION_STATUS = LOCAL_ARCHITECTURAL_DERIVATION_CANDIDATE
AUTHORITY_EFFECT = NONE
IDENTITY_EFFECT = NONE
CANON_EFFECT = NONE

A later source ingestion layer must preserve provenance, locator, edition/date, content hash where applicable, licensing/access class, and retrieval tags.

A later REIS OS knowledge record must preserve external evidence refs, REIS OS invariant refs, derivation, falsification attempts, tests, status, supersedes links, creator OCS, and AUTHORITY_EFFECT = NONE.

## Physiological target

BOOT
→ LOAD_CONSTITUTION
→ RECOVER_STATE
→ BIND_ACTIVE_IDENTITY
→ LOAD_EXPERTISE_MANIFEST
→ UNDERSTAND
→ FORMULATE
→ PROBLEM_CLASSIFICATION
→ SELECT_EXPERT_LENSES
→ RETRIEVE_EXPERT_EVIDENCE
→ RETRIEVE_OTHER_EVIDENCE
→ PLAN
→ CHECK_SCOPE
→ CHECK_AUTHORITY
→ CHECK_EVIDENCE
→ ACT
→ TRACE
→ VERIFY
→ PERSIST
→ LEARN
→ CHECKPOINT
→ IDENTITY_REVALIDATION

This first slice materializes the manifest and lens-selection contract only. Runtime retrieval wiring, persistent corpus ingestion, provenance store, conflict scoring, source-quality scoring, applicability scoring, architectural derivation persistence, and adversarial runtime qualification remain open.

## Acceptance for this slice

- Dédala-only optional capability.
- Four lens families represented as technical lenses, not personas.
- Problem-based selection is deterministic for the declared lexical tags.
- No expert source can alter identity, authority, or canon.
- Unmatched problems do not invent an expert lens.
- Dedicated tests and CI gate are present.

## Explicit non-claims

EXPERT_CORPUS_INGESTED = FALSE
LIVE_RETRIEVAL = FALSE
SOURCE_PROVENANCE_STORE = NOT_IMPLEMENTED
SOURCE_QUALITY_SCORING = NOT_IMPLEMENTED
CONFLICT_DETECTION = NOT_IMPLEMENTED
REIS_OS_KNOWLEDGE_PERSISTENCE = NOT_IMPLEMENTED
RUNTIME_PHYSIOLOGY_WIRING = NOT_IMPLEMENTED
GENERALIZATION_TO_OTHER_OCS = NOT_AUTHORIZED_BY_THIS_SLICE
GLOBAL_PASS = NOT_CLAIMED
