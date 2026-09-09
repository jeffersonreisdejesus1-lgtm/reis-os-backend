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

DÉDALA: exact evidence/provenance, self-assurance denial, causal/architecture review boundary.  
ÁGORA: exact implementation object/head evidence binding, missing evidence never equals PASS, verification remains distinct from independent assurance.  
SOFIA: exact repository object/head, owner-scoped writes, no merge/promotion authority from implementation or tests.  
MÊTIS: explicit evidence freshness, source provenance, uncertainty preservation and strategy != execution authority.  
AURI: system-of-record != authority, historical V0.4 provenance remains unresolved and distinct, no cross-OCS identity/memory merge.  
SYNERGEIA: channel authority required, delivery package identity stable, return receipt binds original delivery, handoff != authority transfer.  
LYRA: `CSP-LYRA-vNEXT-CORR-001` precedence, brand identity != constitutional OCS identity, no implicit ownership transfer or canonical brand promotion.

## Qualification status

QUALIFICATION_TESTS = MATERIALIZED  
LOCAL_TEST_EXECUTION = NOT_EXECUTED_BY_THIS_COMMIT  
HOSTED_CI_PASS = NOT_PROVEN  
INDEPENDENT_CONFORMANCE = NOT_STARTED

The test suite contains common and target-specific adversarial checks. Test presence is not test execution evidence.

`IMPLEMENTED != VERIFIED != ASSURED != PROMOTED`
