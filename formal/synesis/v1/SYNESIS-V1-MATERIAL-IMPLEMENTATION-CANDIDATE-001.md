# SYNESIS-V1-MATERIAL-IMPLEMENTATION-CANDIDATE-001

PROGRAM = REIS-OS-10OCS-REFACTOR-V1-ROLLOUT-001
TARGET_OCS = SÝNESIS
IMPLEMENTER = ÁGORA
SOURCE_ARCHITECTURE = SYNESIS-V1-LOCAL-REFACTOR-ARCHITECTURE-001
SOURCE_ASSURANCE = NOESIS-SYNESIS-V1-A2-REASSURANCE-002
SOURCE_I0 = SYNESIS-V1-IMPLEMENTATION-ARCHITECTURE-I0-001
IMPLEMENTATION_CLASS = I1_MATERIAL_CANDIDATE

## Materialized local Governors

- GOV-SYNESIS-01 = ASSURANCE_INTAKE_INDEPENDENCE_GOVERNOR
- GOV-SYNESIS-02 = EVIDENCE_SUFFICIENCY_PROVENANCE_GOVERNOR
- GOV-SYNESIS-03 = CLAIM_RESERVATION_FINDING_GOVERNOR
- GOV-SYNESIS-04 = REASSURANCE_ROUTING_RECOVERY_GOVERNOR

NOESIS_ROSTER_COPY = FALSE

## Exact R1–R6 ↔ R7 bindings

- SYNESIS-V1-R1-R7-ASSURANCE-STATE-CONTRACT-001
- SYNESIS-V1-R2-R7-COVERAGE-EFFECTIVENESS-CONTRACT-001
- SYNESIS-V1-R3-R7-ASSURANCE-TRANSITION-CONTRACT-001
- SYNESIS-V1-R4-R7-ASSURANCE-SCHEDULING-CONTRACT-001
- SYNESIS-V1-R5-R7-EVIDENCE-PROVENANCE-CONTRACT-001
- SYNESIS-V1-R6-R7-INDEPENDENCE-AUTHORITY-CONTRACT-001

## Fail-closed implementation properties

- local state namespaces and explicit owner map;
- cross-OCS writes denied with zero mutation;
- self-assurance and self-homologation denied;
- canonical promotion and runtime Governor activation denied;
- handoff does not transfer authority;
- object/version binding required;
- stale, unknown, conflicted and partial evidence HOLD;
- evidence and provenance required;
- `REF-SYNESIS-LOCAL-001` explicitly rejected as VOID predecessor;
- reservations cannot be collapsed into PASS;
- PASS_WITH_RESERVATIONS requires explicit reservation refs;
- idempotent request replay;
- snapshot recovery revalidates identity, architecture, A2 assurance, I0 identity, bindings, roster, owner map, generation owners and reservations;
- successful recovery fences pre-recovery writers by advancing every Governor generation.

## Preserved reservations

- N_SYN_RUNTIME_ASSURANCE = HOLD_NON_BLOCKING
- ANATOMICAL_PARITY = UNPROVEN
- DEEP_ANATOMICAL_PARITY_PROVEN = 0/10
- CR3_GLOBAL_FUNCTIONAL_PLENITUDE = NOT_PROVEN
- GLOBAL_REAL_OCS_GOVERNANCE = NOT_PROVEN_WHERE_PREVIOUSLY_RESERVED

## Qualification evidence materialized

`tests/test_synesis_v1_runtime.py` includes adversarial cases for:

- self-assurance;
- self-homologation;
- missing object/version binding;
- missing evidence/provenance;
- stale/unknown/conflicted/partial evidence;
- invalid VOID predecessor injection;
- cross-OCS write;
- foreign/unowned state key;
- reservation-to-PASS collapse;
- explicit PASS_WITH_RESERVATIONS requirements;
- idempotent replay;
- recovery foreign-key injection;
- wrong-owner key placement;
- omitted Governor;
- omitted generation owner;
- reservation drift;
- stale pre-recovery writer;
- valid post-recovery generation writer.

TESTS_MATERIALIZED = YES
TESTS_EXECUTED_BY_THIS_RECORD = NO
HOSTED_CI_PASS = NOT_PROVEN

## Authority boundary

MERGE = NOT_AUTHORIZED
CANONICAL_PROMOTION = NOT_AUTHORIZED
RUNTIME_GOVERNOR_ACTIVATION = NOT_AUTHORIZED
SELF_ASSURANCE = FORBIDDEN
SELF_HOMOLOGATION = FORBIDDEN
AUTHORITY_EXPANSION = NONE

NEXT_GATE = ÁGORA_ENGINEERING_QUALIFICATION
