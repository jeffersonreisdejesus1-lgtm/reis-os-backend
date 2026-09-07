# A0 — ATLAS CONTRACT CLOSURE REPAIR

DOC_ID = A0-ATLAS-CONTRACT-CLOSURE-REPAIR-001
OBJECT = CP-PHYSIO-ATLAS-GRAPH-IMPL-001
STATUS = CANDIDATE_FOR_SYNESIS_REENTRY
OWNER_SPEC = DÉDALA
ORCHESTRATION = NÓESIS
IMPLEMENTATION = NOT_AUTHORIZED
POSTGRES_APPLY = NOT_AUTHORIZED
COMMAND_UI = NOT_AUTHORIZED
FOUNDER_PROMOTION = NOT_PERFORMED

## 0. Scope and governing sequence

This document closes the bounded A0 contract findings only. It does not authorize A1 implementation, persistence, hydration, Command projection, ten-OCS expansion, or AI overlay.

SEQUENCE_INVARIANT:

SEMANTICS -> REFUSAL -> CAUSAL_PROOF -> PERSISTENCE -> HYDRATION -> API -> COMMAND -> TEN_OCS -> AI

GRAPH_TECH_BEFORE_SEMANTIC_PROOF = PROHIBITED
DDL_AUTHORED_MAY_EXIST = TRUE
DDL_APPLIED_IN_A0 = FALSE

## 1. Graph identity separation

ATLAS_DEFINITION_GRAPH != CAUSAL_EVENT_GRAPH
ATLAS_EDGE_TYPES != RUNTIME_CAUSAL_EDGE_TYPES
NO_SCHEMA_REUSE_BY_DEFAULT = TRUE

`ATLAS_DEFINITION_GRAPH` is a definition/anatomy graph. It describes institutional physiology, composition, decomposition, interfaces, protocols, observability points, evidence pointers, authority boundaries, and declared causal semantics.

`CAUSAL_EVENT_GRAPH` is a runtime/execution graph. It records materially observed execution causality.

No Atlas node, edge, event, identifier, or schema may be interpreted as runtime causal evidence solely because an isomorphic or similarly named runtime object exists.

STRUCTURAL_EDGE != RUNTIME_CAUSAL_EVENT
DECLARED_CAUSAL_RULE != OBSERVED_CAUSAL_EVENT
ATLAS_EXISTENCE != CAUSAL_CONSUMPTION

Finding closure target: SYN-ATLAS-001.

## 2. Closed edge vocabulary and zoom semantics

A0 edge vocabulary is closed. Implementations MUST reject unknown edge types.

Allowed Atlas edge classes:

- COMPOSED_OF
- DECOMPOSES_INTO
- DEPENDS_ON
- INTERACTS_VIA
- GOVERNED_BY
- OBSERVED_BY
- EVIDENCED_BY
- LIMITED_BY
- BINDS_TO
- RECOVERS_FROM
- DECLARES_CAUSAL_RELATION
- CONTRADICTS

No edge is transitively materialized unless its edge definition explicitly sets `transitivity = ALLOWED` and supplies a transitivity rule id.

Default:

ZOOM_TRANSITIVITY = DENY
IMPLICIT_EDGE_MATERIALIZATION = DENY

A zoom operation may hide intermediate nodes for presentation, but it MUST NOT create an inferred edge, alter edge identity, or change causal semantics. A collapsed presentation path carries `presentation_only = true` and preserves the ordered underlying edge ids.

Finding closure target: SYN-ATLAS-007.

## 3. Semantic payload signature

```text
SemanticPayloadSignature {
  purpose = INTEGRITY_ONLY
  signer_id
  key_id
  algorithm
  signed_catalog_sha256
}
```

Signature semantics are strictly limited to byte/semantic-integrity attestation of the referenced semantic catalog identity.

SIGNATURE != AUTHORITY
SIGNATURE != ASSURANCE
SIGNATURE != PROMOTION
SIGNATURE != EXECUTION_PERMISSION
SIGNATURE != TRUTH

A verifier may conclude only that the signature is cryptographically valid for the stated key and hash. Authority, promotion, assurance, and execution state require their own independent evidence and gates.

Finding closure target: SYN-ATLAS-002.

## 4. Canonical catalog identity

Two identities are mandatory:

- `YAML_SOURCE_SHA`: SHA-256 of exact source bytes as stored.
- `SEMANTIC_CATALOG_SHA`: SHA-256 of deterministic canonical semantic encoding.

`SEMANTIC_CATALOG_SHA` MUST NOT depend on YAML comments, presentation ordering where the schema defines maps as unordered, aliases, anchors, quoting style, indentation, or other serialization-only variation.

### 4.1 Canonical normalization

CANONICAL_NORMALIZATION_VERSION = `atlas-semantic-v1`

Normalization pipeline:

1. Parse YAML with aliases resolved.
2. Reject duplicate mapping keys.
3. Reject unknown schema fields.
4. Convert all schema-defined maps to canonical objects with lexicographically sorted UTF-8 keys.
5. Preserve array order only where schema marks order as semantic.
6. For schema-defined set-like arrays, normalize by unique semantic identifier and sort lexicographically by that identifier.
7. Normalize booleans/nulls to JSON primitives.
8. Normalize integers and decimals to their schema-defined numeric representation; exponent notation is forbidden in canonical output.
9. Normalize strings to Unicode NFC.
10. Remove comments, anchors, aliases, tags used only for YAML presentation, and non-semantic whitespace.
11. Emit UTF-8 JSON, `ensure_ascii=false`, sorted object keys, separators `(',', ':')`, no trailing newline.
12. SHA-256 the emitted bytes and prefix stored form with `sha256:`.

Any future normalization change requires a new normalization version and MUST NOT silently reinterpret an existing semantic hash.

ROLLBACK_BY_SHA means rollback by `SEMANTIC_CATALOG_SHA`, not by YAML byte hash.

### 4.2 Required proofs

T26 = BLOCKING_A1

Same semantic catalog + different YAML formatting/order/aliases/comments -> SAME_SEMANTIC_CATALOG_SHA.

A2 later additionally requires canonical-hash persistence roundtrip and rollback-by-semantic-sha.

Finding closure target: SYN-ATLAS-003.

## 5. AntiThesis deterministic evaluation

`AntiThesisMatcher(QueryPlan, ProposedClaim)` MUST be deterministic.

Evaluation order:

1. Evaluate every applicable anti-thesis rule against the same immutable input snapshot.
2. Preserve every match in `matches[]` ordered by `(priority ASC, rule_id ASC)`.
3. A rule result is one of `DENY`, `CAP`, `ANNOTATE`, `NO_MATCH`.
4. `DENY` dominates all non-DENY results.
5. If one or more DENY rules match, final decision = DENY. Evaluation still records all applicable matches; no hidden short-circuit may erase evidence.
6. If no DENY matches, apply all CAP rules using the severity aggregation rules in section 6.
7. ANNOTATE never upgrades severity and never converts DENY to allow.
8. Client/user/UI input cannot reorder rules, suppress matches, or override the result.
9. Equal-priority rules are ordered by stable `rule_id` lexical order solely for reproducibility; ordering does not change dominance semantics.

MULTIPLE_MATCHES = PRESERVED
CLIENT_OVERRIDE = PROHIBITED
HIDDEN_SHORT_CIRCUIT = PROHIBITED

Finding closure target: SYN-ATLAS-004.

## 6. Severity lattice and multipath aggregation

Classification/severity uses an explicit total order:

`NONE < INFO < LOW < MEDIUM < HIGH < CRITICAL < DENY`

For all operations below, `rank(x)` is the position in that order.

### 6.1 Per-rule

Each causal/thesis rule defines `rule_cap`.

`rule_result = min(proposed_result, rule_cap)` by rank.

A rule may reduce/cap but MUST NOT upgrade the input severity unless the rule explicitly represents a DENY condition.

### 6.2 Per-path

For a valid path P with rule results `r1..rn`:

`path_result = max(r1..rn)` by rank, then capped by `path_cap` if defined.

### 6.3 Cross-path

For valid independent paths `p1..pm` supporting the same proposed claim:

`cross_path_result = max(path_result(p1)..path_result(pm))` by rank.

### 6.4 Global thesis cap

`final_non_deny_result = min(cross_path_result, thesis_global_cap)` by rank.

### 6.5 NEVER_UPGRADES

For every non-DENY transformation step:

`rank(output) <= max(rank(inputs))`

No composition, additional path, evidence pointer, observation, or presentation operation may elevate a classification above the strongest authorized input. DENY remains a separate dominating refusal state.

SEVERITY_LAUNDERING = PROHIBITED

Finding closure targets: SYN-ATLAS-005, SYN-ATLAS-010.

## 7. Evidence pointer versus observed evidence

`EVIDENCE_POINTER` is a reference only. It proves that a definition points to an evidence location or evidence identity.

`OBSERVED_EVIDENCE` requires successful read/verification of that evidence through an authorized observation path and a material observation result.

EVIDENCE_POINTER != OBSERVED_EVIDENCE
POINTER_EXISTENCE != EVIDENCE_VALIDITY
OBSERVATION_FAILURE -> NOT_PROVEN
OBSERVATION_FAILURE != NEGATIVE_PROOF

`EVIDENCED_BY` Atlas edges MUST carry `evidence_mode = POINTER` in A0/A1 definition catalogs. Runtime observation state is never embedded into the static edge as though it were live evidence.

Finding closure target: SYN-ATLAS-008.

## 8. L5 precedence glossary

The following identifiers are resolved for this contract:

- KR = Kernel authoritative policy/identity state
- HZ = Hazel durable continuity/event state
- MJ = Mission Journal durable mission state
- GR = Graph/Atlas Registry definition state
- RB = material readback result
- OBS = operational observability signal
- CI = continuous-integration evidence
- NT = non-authoritative narrative/textual statement

Precedence for conflicting L5 inputs:

`KR/HZ > MJ > GR > RB > OBS > CI/NT`

`KR/HZ` are co-top only when they address different authoritative dimensions. If KR and HZ materially conflict on the same dimension, result = `CONFLICT_NOT_PROVEN`; neither silently overrides the other.

Precedence selects which source may constrain a claim. It MUST NOT manufacture evidence absent from the winning source.

Finding closure target: SYN-ATLAS-009.

## 9. Catalog release serving semantics

```text
CatalogRelease {
  release_id
  semantic_catalog_sha
  predecessor_release_id | null
  status = CANDIDATE | PROMOTED | SUPERSEDED | REVOKED
  promoted_at | null
  superseded_at | null
}

ServedCatalogPointer {
  served_catalog_release_id
}
```

Invariants:

- Exactly one `served_catalog_release_id` exists per Atlas catalog scope.
- The served release MUST have `status = PROMOTED`.
- Promotion of a successor and supersession of its predecessor are one atomic state transition.
- A release cannot be both served and SUPERSEDED/REVOKED.
- Two PROMOTED historical rows may exist only if exactly one is the served current pointer; `PROMOTED` alone does not mean current.
- T21 evaluates the served pointer, not a query for any row with status PROMOTED.

Finding closure target: SYN-ATLAS-012.

## 10. Test/gate binding

Tests are promotion blockers, not advisory artifacts.

### A1 BLOCKING

T1 T2 T3 T4 T12 T13 T16 T17 T18 T23 T25 T26

plus:
- deterministic matcher semantics
- canonical hash specification conformance
- closed vocabulary rejection
- graph identity separation assertion

### A2 BLOCKING

T21
+ canonical-hash persistence roundtrip
+ rollback-by-semantic-sha
+ exactly-one-served-release invariant

### A3 BLOCKING

T5 T6 T7 T8 T9 T10 T11 T14 T15 T19 T22

T6 and T15 MUST have distinct entry points:
- T6 = direct causal-evaluation entry point with a FENCED authoritative input versus green observability.
- T15 = hydrated/multipath evaluation entry point where a FENCED authoritative input competes with green OBS during composition.

They prove the same dominance invariant at different system boundaries and are not interchangeable.

### A4 BLOCKING

Repeat A3 against stage systems of record.

### A5 BLOCKING

T20
+ API isolation/access/disclosure tests.

### A6 BLOCKING

All prior gates PASS.

### A7 BLOCKING

UNKNOWN_DEFINITION
+ zero-analogy proof.

### A8 BLOCKING

T24
+ deterministic-package reproducibility.

Finding closure targets: SYN-ATLAS-006, SYN-ATLAS-011.

## 11. T25 — structure versus causal semantics

T25 = BLOCKING_A1

Fixture:

same structural graph
+ thesis/rule package A
+ thesis/rule package B

Expected:

- structural node/edge identities remain byte/semantic-identical;
- authorized causal results differ when rule packages differ;
- no structural mutation is required to produce the semantic difference.

Proves:

STRUCTURE != CAUSAL_SEMANTICS

This is a semantic-kernel proof, not a persistence proof.

## 12. T26 — serialization versus semantic identity

T26 = BLOCKING_A1

Fixture:

identical semantic catalog represented by YAML variants differing only in formatting, map order, comments, quoting, anchors/aliases, and non-semantic whitespace.

Expected:

YAML_SOURCE_SHA may differ.
SEMANTIC_CATALOG_SHA MUST be identical.

Proves:

SERIALIZATION != SEMANTIC_IDENTITY

## 13. Finding closure matrix

| Finding | Closure mechanism | Target state |
|---|---|---|
| SYN-ATLAS-001 | §§1–2 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-002 | §3 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-003 | §4 + T26 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |
| SYN-ATLAS-004 | §5 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-005 | §6 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-006 | §10 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-007 | §2 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-008 | §7 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-009 | §8 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-010 | §6 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-011 | §10 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-012 | §9 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |

No row in this matrix self-declares assurance PASS. Final closure is reserved to independent SÝNESIS re-entry.

## 14. A0 exit criteria

A0 may be declared PASS only if independent assurance confirms all of the following:

- all 12 findings are materially closed by this contract or an explicitly referenced companion contract;
- T25 and T26 are accepted as A1 blocking proofs;
- no semantic ambiguity remains that permits two conforming implementations to produce different refusal, severity, release-current, or semantic-hash results for identical inputs;
- no persistence or graph technology is required to establish the above semantics;
- no A1 implementation has been smuggled into A0.

Until then:

A0 = HOLD_FOR_ASSURANCE_REENTRY
A1 = NOT_AUTHORIZED
POSTGRES_APPLY = NOT_AUTHORIZED
REAL_L5 = NOT_AUTHORIZED
COMMAND = NOT_AUTHORIZED
TEN_OCS = NOT_AUTHORIZED
AI = NOT_AUTHORIZED
