# A0 — ATLAS CONTRACT CLOSURE REPAIR

DOC_ID = A0-ATLAS-CONTRACT-CLOSURE-REPAIR-001
OBJECT = CP-PHYSIO-ATLAS-GRAPH-IMPL-001
STATUS = CANDIDATE_FOR_SYNESIS_REENTRY_R2
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

`ATLAS_DEFINITION_GRAPH` is a definition/anatomy graph. It describes institutional physiology and declared semantics. `CAUSAL_EVENT_GRAPH` is a runtime/execution graph and records materially observed execution causality.

STRUCTURAL_EDGE != RUNTIME_CAUSAL_EVENT
DECLARED_CAUSAL_RULE != OBSERVED_CAUSAL_EVENT
ATLAS_EXISTENCE != CAUSAL_CONSUMPTION

Finding closure target: SYN-ATLAS-001.

## 2. Closed v0 edge vocabulary and zoom semantics

The original v0 vocabulary is normative and remains closed.

Allowed Atlas v0 edge types, exactly:

- COMPOSES
- REQUIRES
- GOVERNED_BY
- EVIDENCED_BY

Any other edge type is rejected in A0/A1.

`DEPENDS_ON` is explicitly prohibited in v0. Encountering `DEPENDS_ON` or any other non-v0 edge type produces `HOLD_UNKNOWN_EDGE_TYPE`; it MUST NOT be coerced, aliased, inferred, or silently mapped to one of the four allowed types.

V0_EDGE_VOCABULARY_REOPEN = PROHIBITED
DEPENDS_ON = PROHIBITED_V0
UNKNOWN_EDGE_TYPE -> HOLD_UNKNOWN_EDGE_TYPE

Zoom is presentation only:

ZOOM_TRANSITIVITY = DENY
IMPLICIT_EDGE_MATERIALIZATION = DENY

A zoom operation may hide intermediate nodes, but MUST NOT create a new edge, change the type of an underlying edge, alter edge identity, or create causal meaning. A collapsed path carries only ordered underlying edge ids plus `presentation_only = true`.

Finding closure target: SYN-ATLAS-007 and SÝNESIS re-entry blocker 1.

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

SIGNATURE != AUTHORITY
SIGNATURE != ASSURANCE
SIGNATURE != PROMOTION
SIGNATURE != EXECUTION_PERMISSION
SIGNATURE != TRUTH

A valid signature proves only cryptographic integrity for the stated key and semantic catalog hash.

Finding closure target: SYN-ATLAS-002.

## 4. Canonical catalog identity

Two identities are mandatory:

- `YAML_SOURCE_SHA`: SHA-256 of exact source bytes.
- `SEMANTIC_CATALOG_SHA`: SHA-256 of deterministic canonical semantic encoding.

CANONICAL_NORMALIZATION_VERSION = `atlas-semantic-v1`

### 4.1 Fully closed canonicalization rules

The following rules are complete for `atlas-semantic-v1`; no future schema is permitted to change their meaning.

1. Parse YAML with aliases resolved.
2. Reject duplicate mapping keys.
3. Reject unknown schema fields.
4. Normalize every mapping as an unordered object; keys are Unicode-NFC strings sorted lexicographically by UTF-8 byte sequence.
5. Every array in `atlas-semantic-v1` is order-significant. Array element order is preserved exactly after scalar/object normalization. There are no set-like arrays in v1.
6. Therefore, YAML mapping-key reordering is non-semantic; YAML array-element reordering is semantic and MUST change `SEMANTIC_CATALOG_SHA` unless the resulting ordered sequence is identical.
7. Strings normalize to Unicode NFC and otherwise preserve exact code-point content.
8. Booleans normalize to JSON `true`/`false`; null normalizes to JSON `null`.
9. Integers normalize to base-10 digits with optional leading `-`, no leading plus, and no leading zero except the value `0`; `-0` normalizes to `0`.
10. Decimal values are parsed as exact decimals, never binary floats. Canonical decimal form uses base-10 fixed notation only: no exponent, no leading plus, no unnecessary leading zeroes, trailing fractional zeroes removed, decimal point removed if the fraction becomes empty, and any negative zero normalizes to `0`.
11. NaN, positive/negative infinity, YAML sexagesimal values, and implementation-specific numeric tags are rejected.
12. YAML comments, anchors, aliases after resolution, quoting style, indentation, line endings, presentation-only tags, and non-semantic whitespace do not enter canonical output.
13. Emit UTF-8 JSON with `ensure_ascii=false`, sorted object keys, separators `(',', ':')`, and no trailing newline.
14. SHA-256 the emitted bytes; stored form is `sha256:<64 lowercase hex>`.

No conforming implementation may choose a different array policy, numeric grammar, Unicode normalization, or map ordering under `atlas-semantic-v1`.

Any future change requires a new normalization-version identifier and cannot reinterpret existing hashes.

ROLLBACK_BY_SHA = ROLLBACK_BY_SEMANTIC_CATALOG_SHA

### 4.2 Required proof

T26 = BLOCKING_A1

Two YAML documents that differ only by comments, indentation, quoting style, aliases/anchors, line endings, non-semantic whitespace, or mapping-key order MUST produce the same `SEMANTIC_CATALOG_SHA`.

T26 explicitly does NOT treat array-element reordering as serialization-only variation.

Finding closure target: SYN-ATLAS-003 and SÝNESIS re-entry blocker 3.

## 5. AntiThesis deterministic evaluation

`AntiThesisMatcher(QueryPlan, ProposedClaim)` MUST be deterministic.

1. Evaluate every applicable anti-thesis rule against the same immutable input snapshot.
2. Preserve all matches ordered by `(priority ASC, rule_id ASC)`.
3. Rule decision is one of `DENY`, `CAP`, `ANNOTATE`, `NO_MATCH`.
4. `DENY` is a refusal decision domain and is not a severity value.
5. One or more DENY matches => final refusal decision = DENY, while all matches remain preserved.
6. Without DENY, apply CAP using section 6.
7. ANNOTATE cannot alter severity or refusal.
8. Client/UI cannot reorder, suppress, or override matches.
9. No hidden short-circuit may erase evaluated evidence.

MULTIPLE_MATCHES = PRESERVED
CLIENT_OVERRIDE = PROHIBITED
HIDDEN_SHORT_CIRCUIT = PROHIBITED

Finding closure target: SYN-ATLAS-004.

## 6. Original severity domain and multipath aggregation

The original candidate severity domain is preserved exactly:

`NONE < INFORMATIONAL < DEGRADE < HOLD < FAIL`

Equivalent descending statement:

`FAIL > HOLD > DEGRADE > INFORMATIONAL > NONE`

`DENY` is NOT a severity and MUST NOT appear in this ordering. Refusal decision and severity are separate fields/domains.

### 6.1 Per-rule cap

Each causal/thesis rule may define `rule_cap` in the five-value severity domain.

`rule_result = min(input_severity, rule_cap)` by the normative order above.

If no cap applies, `rule_result = input_severity`.

NEVER_UPGRADES applies to every severity transformation.

### 6.2 Per-path

For a valid path with rule results `r1..rn`:

`path_result = max(r1..rn)` using the original severity order.

If a `path_cap` exists:

`path_result = min(path_result, path_cap)`.

### 6.3 Cross-path

For valid independent paths supporting the same claim:

`cross_path_result = max(path_result(p1)..path_result(pm))`.

This selects the strongest existing authorized severity; path multiplicity by itself cannot raise severity beyond the strongest path.

### 6.4 Global thesis cap

`final_severity = min(cross_path_result, thesis_global_cap)` when a thesis cap exists; otherwise `final_severity = cross_path_result`.

### 6.5 NEVER_UPGRADES

For each severity transformation:

`rank(output) <= max(rank(inputs))`

Additional paths, evidence pointers, observations, composition, or presentation cannot introduce a severity not already present in an authorized input or cap domain.

SEVERITY_LAUNDERING = PROHIBITED
REFUSAL_DECISION != SEVERITY

Finding closure targets: SYN-ATLAS-005, SYN-ATLAS-010, and SÝNESIS re-entry blocker 2.

## 7. Evidence pointer versus observed evidence

`EVIDENCE_POINTER` is reference identity only.

`OBSERVED_EVIDENCE` requires successful authorized observation/read plus a material observation result.

EVIDENCE_POINTER != OBSERVED_EVIDENCE
POINTER_EXISTENCE != EVIDENCE_VALIDITY
OBSERVATION_FAILURE -> NOT_PROVEN
OBSERVATION_FAILURE != NEGATIVE_PROOF

`EVIDENCED_BY` in the static Atlas remains a pointer relation. It MUST NOT be read as live observation solely from edge existence.

Finding closure target: SYN-ATLAS-008.

## 8. L5 precedence glossary

- KR = Kernel authoritative policy/identity state
- HZ = Hazel durable continuity/event state
- MJ = Mission Journal durable mission state
- GR = Graph/Atlas Registry definition state
- RB = material readback result
- OBS = operational observability signal
- CI = continuous-integration evidence
- NT = non-authoritative narrative/textual statement

Precedence:

`KR/HZ > MJ > GR > RB > OBS > CI/NT`

If KR and HZ materially conflict on the same authoritative dimension, result = `CONFLICT_NOT_PROVEN`; neither silently overrides the other.

Precedence constrains claims; it never manufactures absent evidence.

Finding closure target: SYN-ATLAS-009.

## 9. Catalog scope and served release semantics

The v0 catalog scope identity is a normative constant:

`catalog_scope_id = "reis-os/control-plane/physiology-atlas/v0"`

No alternate scope key, alias, tenant-derived value, UI label, release id, or runtime-generated identifier may represent this v0 scope.

`catalog_scope_id` identifies the catalog namespace. `release_id` identifies one release inside that scope.

```text
CatalogRelease {
  catalog_scope_id
  release_id
  semantic_catalog_sha
  predecessor_release_id | null
  status = CANDIDATE | PROMOTED | SUPERSEDED | REVOKED
  promoted_at | null
  superseded_at | null
}

ServedCatalogPointer {
  catalog_scope_id
  served_catalog_release_id
}
```

Invariants:

- Every `CatalogRelease` in v0 MUST have the exact normative `catalog_scope_id` above.
- Exactly one `ServedCatalogPointer` exists for that `catalog_scope_id`.
- The pointer target MUST be a release in the same scope with `status = PROMOTED`.
- Promotion of a successor, supersession of its predecessor, and pointer movement are one atomic transition.
- A release cannot be served while SUPERSEDED or REVOKED.
- `PROMOTED` alone does not mean current; current means `release_id == served_catalog_release_id` for the normative scope.
- T21 evaluates this exact scope key and served pointer.

Finding closure target: SYN-ATLAS-012 and SÝNESIS re-entry blocker 4.

## 10. Test/gate binding

Tests are promotion blockers, not advisory artifacts.

### A1 BLOCKING

T1 T2 T3 T4 T12 T13 T16 T17 T18 T23 T25 T26

plus:
- deterministic matcher semantics
- canonical hash conformance
- exact v0 edge vocabulary rejection
- explicit `DEPENDS_ON -> HOLD_UNKNOWN_EDGE_TYPE`
- graph identity separation assertion
- original severity-domain conformance
- normative catalog-scope identity assertion

### A2 BLOCKING

T21
+ canonical-hash persistence roundtrip
+ rollback-by-semantic-sha
+ exactly-one-served-release invariant for the normative `catalog_scope_id`

### A3 BLOCKING

T5 T6 T7 T8 T9 T10 T11 T14 T15 T19 T22

T6 = direct causal-evaluation entry point with FENCED authoritative input versus green OBS.
T15 = hydrated/multipath entry point with FENCED authoritative input versus green OBS during composition.

### A4 BLOCKING

Repeat A3 against stage systems of record.

### A5 BLOCKING

T20 + API isolation/access/disclosure.

### A6 BLOCKING

All prior gates PASS.

### A7 BLOCKING

UNKNOWN_DEFINITION + zero-analogy proof.

### A8 BLOCKING

T24 + deterministic-package reproducibility.

Finding closure targets: SYN-ATLAS-006, SYN-ATLAS-011.

## 11. T25 — structure versus causal semantics

T25 = BLOCKING_A1

Same structural graph + thesis/rule package A + thesis/rule package B -> potentially different authorized causal results while structural node/edge identities remain identical.

Proves:

STRUCTURE != CAUSAL_SEMANTICS

## 12. T26 — serialization versus semantic identity

T26 = BLOCKING_A1

Equivalent semantic catalogs that differ only in non-semantic YAML serialization characteristics defined in section 4.2 -> SAME_SEMANTIC_CATALOG_SHA.

SERIALIZATION != SEMANTIC_IDENTITY

## 13. Finding closure matrix

| Finding | Closure mechanism | Target state |
|---|---|---|
| SYN-ATLAS-001 | §§1–2 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-002 | §3 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-003 | §4 + T26 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |
| SYN-ATLAS-004 | §5 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-005 | §6 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |
| SYN-ATLAS-006 | §10 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-007 | §2 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-008 | §7 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-009 | §8 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-010 | §6 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |
| SYN-ATLAS-011 | §10 | CLOSED_BY_CONTRACT |
| SYN-ATLAS-012 | §9 | CLOSED_BY_CONTRACT_PENDING_SYNESIS |

SÝNESIS re-entry regressions addressed in this revision:

- R1 vocabulary reopening -> §2
- R2 severity replacement -> §§5–6
- R3 incomplete canonicalization -> §4
- R4 undefined catalog scope -> §9

No row self-declares assurance PASS.

## 14. A0 exit criteria

A0 may be PASS only after independent SÝNESIS confirms:

- the original v0 edge vocabulary is preserved without `DEPENDS_ON`;
- the original five-value severity domain is preserved and refusal remains separate;
- canonicalization is fully deterministic under `atlas-semantic-v1` without schema-deferred array or numeric semantics;
- the normative `catalog_scope_id` makes exactly-one-current unambiguous;
- the original 12 findings remain materially closed;
- T25 and T26 remain accepted as A1 blockers;
- no persistence or graph technology is required to prove the semantic contract;
- no A1 implementation has entered A0.

Until then:

A0 = HOLD_FOR_ASSURANCE_REENTRY
A1 = NOT_AUTHORIZED
POSTGRES_APPLY = NOT_AUTHORIZED
REAL_L5 = NOT_AUTHORIZED
COMMAND = NOT_AUTHORIZED
TEN_OCS = NOT_AUTHORIZED
AI = NOT_AUTHORIZED
