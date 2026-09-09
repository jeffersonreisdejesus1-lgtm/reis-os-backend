# Íris V1 Material Implementation Candidate 001

MISSION_ID = REIS-OS-OCS-REFACTOR-V1-IRIS-001
IMPLEMENTER = ÁGORA
SOURCE_ARCHITECTURE = IRIS-V1-IMPLEMENTATION-ARCHITECTURE-I0-001
SOURCE_ASSURANCE = SYNESIS-INDEPENDENT-ASSURANCE-IRIS-V1-A2-001
CLASS = LOCAL_V1_MATERIAL_IMPLEMENTATION_CANDIDATE

## Preserved roots

IDENTITY_STATE_ROOT = EC-IRIS-GENERALIST-EVO-001 + IRIS_STATE.json
DESIGN_AUTHORITY = IRIS
LOCAL_SPECIALIZATION = UX_UI + VISUAL_DESIGN + PERCEPTION + INTERACTION + EXPERIENCE + ACCESSIBILITY
AUTHORITY_EXPANSION = NONE

## Derived local population

The implementation contains four locally derived Governors only:

- GOV-IRIS-01 — PERCEPTION_INTERACTION_GOVERNOR
- GOV-IRIS-02 — EXPERIENCE_SCOPE_GOVERNOR
- GOV-IRIS-03 — DESIGN_TRUST_AMBIGUITY_GOVERNOR
- GOV-IRIS-04 — DESIGN_ROUTING_GOVERNOR

ROSTER_SIZE = DERIVED_PROPERTY
NOESIS_17_GOVERNOR_ROSTER_COPY = FALSE
RUNTIME_GOVERNOR_ACTIVATION = NOT_AUTHORIZED

## Deterministic controls

Accessibility, state ownership, evidence/freshness, authority/scope, runtime participation, recovery/fencing and R4 scheduler admission remain deterministic controls rather than Governors.

Runtime construction fails closed unless all six material R1-R6↔R7 binding refs and the exact local derivation reference are supplied.

Accessibility conflict produces HOLD with zero mutation. STALE, UNKNOWN and CONFLICTED evidence cannot support a current-state mutation. Cross-owner and institutional-state writes from Governors are denied. Engineering consumption does not transfer design authority. Authority transfer, material effects, canonical promotion and self-assurance are outside the local R7 runtime boundary.

## Durable roster completeness repair

FINDING_ID = IRIS-V1-DURABLE-ROSTER-COMPLETENESS-001
SOURCE = DÉDALA review 5157861180
REPAIR_OWNER = ÁGORA

Durable restore now requires the restored Governor roster to be exactly the four canonical local Governors. Omission, duplication or substitution fails closed before restored state is admitted.

The generation owner set must equal the restored Governor set exactly. Missing or extra generation owners fail closed.

Adversarial restart qualification includes:
- omitted Governor with recomputed snapshot hash;
- omitted generation owner with recomputed snapshot hash.

Existing durable constraints remain preserved: canonical Governor contracts, binding identity, derivation identity, namespace ownership, identity/state root, design authority, lease validation, idempotency ownership, checkpoint ownership, snapshot integrity and stale-writer fencing.

## Qualification state

The earlier engineering qualification established `24 passed / 0 failed` on the pre-finding qualified code contents. The present repair adds two new adversarial tests; hosted execution on the repaired exact head remains unavailable because GitHub Actions fails before runner assignment.

A Quality Gate rerun on the repaired head again returned `steps=null`.

Therefore:

LOCAL_PRE_REPAIR_QUALIFICATION = 24_PASSED_0_FAILED
NEW_REPAIR_TESTS = MATERIALIZED
NEW_REPAIR_TEST_EXECUTION = NOT_PROVEN_BY_HOSTED_CI
HOSTED_CI = PRE_RUNNER_FAILURE
HOSTED_CI_PASS = NOT_PROVEN
IMPLEMENTATION_TEST_FAILURE = NOT_DEMONSTRATED_BY_HOSTED_CI

## Preserved reservations

RUNTIME_EFFECTIVENESS = NOT_ASSURED
ANATOMICAL_PARITY = UNPROVEN
DEEP_ANATOMICAL_PARITY_PROVEN = 0/10
ACCESSIBILITY_CONFLICT_NEGATIVE_RUNTIME_COVERAGE = LOCALLY_EXECUTED_PASS / INDEPENDENTLY_NOT_YET_ASSURED
GLOBAL_FUNCTIONAL_PLENITUDE = NOT_PROVEN

EXECUTED != VERIFIED
VERIFIED != ASSURED
ASSURED != PROMOTED

MERGE = NOT_AUTHORIZED
CANONICAL_PROMOTION = NOT_AUTHORIZED
GOVERNOR_ACTIVATION = NOT_AUTHORIZED

NEXT_GATE = DÉDALA_REREVIEW
