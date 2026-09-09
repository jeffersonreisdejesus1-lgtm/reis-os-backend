# AGORA-7OCS-V1-MATERIAL-IMPLEMENTATION-CANDIDATE-001

PROGRAM = REIS-OS-10OCS-REFACTOR-V1-ROLLOUT-001  
IMPLEMENTER = ÁGORA  
TARGETS = DÉDALA + ÁGORA + SOFIA + MÊTIS + AURI + SYNERGEIA + LYRA  
SOURCE_ASSURANCE = SYNESIS-7OCS-V1-A2-INDEPENDENT-ASSURANCE-002  
CLASS = MATERIAL_IMPLEMENTATION_CANDIDATE  
CANONICAL_PROMOTION = NOT_AUTHORIZED  
RUNTIME_GOVERNOR_ACTIVATION = NOT_AUTHORIZED  
AUTHORITY_EXPANSION = NONE

## Materialization model

The seven candidates share mechanics only. They do not share identity, state, authority, autobiographical memory, Governor rosters, derivation references or binding identities.

Each target profile freezes:

- exact target identity reference;
- exact local Governor derivation reference;
- exactly four locally-derived Governors;
- exactly six target-specific R1–R6↔R7 binding references;
- target-specific state namespaces and owner-scoped writable keys;
- deterministic policy boundaries and preserved reservations.

Shared mechanics enforce fail-closed construction on wrong derivation or binding references, cross-OCS denial, state-key and namespace ownership, `DENY => MUTATION_COUNT = 0`, and separation of local governance execution from self-assurance, canonical promotion, runtime Governor activation and authority transfer.

## Target-specific deterministic boundaries

DÉDALA: exact evidence/provenance, self-assurance denial, causal inconsistency HOLD and architecture review boundary.  
ÁGORA: runtime is construction-bound to one exact implementation object/head; request mismatch HOLDs; missing evidence never equals PASS; verification remains distinct from independent assurance.  
SOFIA: runtime is construction-bound to one exact repository object/head, owner-scoped writes, no merge/promotion authority from implementation or tests.  
MÊTIS: explicit evidence freshness, source provenance, uncertainty preservation and strategy != execution authority.  
AURI: system-of-record != authority, historical V0.4 provenance remains unresolved and distinct, preserved reservation must survive recovery, no cross-OCS identity/memory merge.  
SYNERGEIA: channel authority required, delivery package identity stable, delivery/return Governor requires a return receipt bound to the original package, handoff != authority transfer.  
LYRA: request must bind to `CSP-LYRA-vNEXT-CORR-001`; brand identity != constitutional OCS identity; no implicit ownership transfer or canonical brand promotion.

## Engineering qualification repair

ENGINEERING_QUALIFICATION_ID = AGORA-7OCS-V1-ENGINEERING-QUALIFICATION-001  
INITIAL_REVIEW_HEAD = ad4a05a348a176776a5871f97deb490831b3ffa0  
QUALIFICATION_RESULT = REPAIR_APPLIED

Static qualification identified material gaps between the I0 contracts and the first candidate implementation:

- AGORA/SOFIA object/head checks only required non-empty request values and were not bound to a construction-time exact object/head;
- recovery/restart and durable roster/generation revalidation were absent;
- stale-writer generation fencing was absent;
- Dédala causal inconsistency had no explicit HOLD path;
- Synergeia delivery/return routing did not require a return receipt;
- Lyra corrected-CSP precedence existed as profile metadata but was not enforced by the runtime;
- preserved reservations were not recovery invariants.

Repairs materialized:

- exact construction-time object/head binding for AGORA and SOFIA;
- exact request equality against bound object/head;
- per-Governor generation fencing and stale-generation denial;
- snapshot/recovery with exact OCS identity, derivation, six bindings, canonical Governor roster, generation-owner set, namespaces, state version, preserved reservations and object/head binding revalidation;
- Dédala causal inconsistency HOLD;
- Synergeia mandatory return receipt for delivery/return routing and exact package binding;
- Lyra corrected-CSP request binding;
- adversarial tests for omitted Governor, omitted generation owner, namespace drift, reservation drift, object/head drift and stale writer fencing.

## Qualification status

QUALIFICATION_TESTS = MATERIALIZED_AND_EXPANDED  
LOCAL_TEST_EXECUTION = NOT_EXECUTED_BY_AGORA_TOOLING  
HOSTED_QUALITY_GATE_RUN = 34401772116  
HOSTED_CI = PRE_RUNNER_FAILURE  
HOSTED_CI_PASS = NOT_PROVEN  
IMPLEMENTATION_TEST_FAILURE = NOT_DEMONSTRATED  
INDEPENDENT_CONFORMANCE = NOT_STARTED

The hosted Quality Gate job completed with no runner steps (`steps = null`). Therefore it is neither implementation PASS nor implementation test failure evidence. Test presence remains distinct from test execution evidence.

`IMPLEMENTED != VERIFIED != ASSURED != PROMOTED`

NEXT_GATE = DEDALA_INDEPENDENT_CONFORMANCE  
MERGE = NOT_AUTHORIZED  
CANONICAL_PROMOTION = NOT_AUTHORIZED  
RUNTIME_GOVERNOR_ACTIVATION = NOT_AUTHORIZED
