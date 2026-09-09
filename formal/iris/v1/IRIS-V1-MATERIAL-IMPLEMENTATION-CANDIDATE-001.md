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

Runtime construction fails closed unless all six canonical R1-R6↔R7 binding identities and the exact local derivation reference are supplied. Governor registration requires the exact locally derived contract, including role, NIR coverage, writable/readable namespaces, owned state keys, allowed operations and authority ceiling.

Accessibility conflict produces HOLD with zero mutation. STALE, UNKNOWN and CONFLICTED evidence cannot support a current-state mutation. Cross-owner, cross-key-owner and institutional-state writes from Governors are denied. Engineering consumption does not transfer design authority. Authority transfer, material effects, canonical promotion and self-assurance are outside the local R7 runtime boundary.

The runtime also materializes idempotent replay, idempotency conflict denial, owner-scoped checkpoints/recovery, generation fencing and conservative invalidation of pre-recovery idempotency keys.

## Durable candidate

`app/iris_v1/durable.py` provides append-only SQLite snapshot persistence with hash integrity, restart validation, exact local Governor-contract revalidation, state-key ownership validation, binding/derivation revalidation and stale-writer reconciliation/fail-closed behavior.

Durable restoration cannot substitute persisted state for architecture or authority. A forged local Governor contract remains invalid even when a modified snapshot is re-hashed; a snapshot modified without re-hashing is rejected as an integrity failure.

## Ágora engineering qualification

QUALIFICATION_ID = AGORA-IRIS-V1-ENGINEERING-QUALIFICATION-001
QUALIFIED_CODE_HEAD = 551ae6b1d30dab266867dafa01f5408f39f06de6
EXECUTION_ENVIRONMENT = LOCAL_ISOLATED_PYTEST
TEST_FILES = tests/test_iris_v1_runtime.py + tests/test_iris_v1_durable.py
TEST_RESULT = 24_PASSED
TEST_FAILURES = 0
EXECUTION_TIME = 0.29s

Qualification coverage includes:

- exact six-binding identity and absence gates;
- exact local derivation gate;
- local roster cardinality and anti-cloning;
- Governor-contract substitution rejection;
- explicit operation and state-key ownership;
- accessibility HOLD with zero mutation;
- evidence freshness non-promotion;
- cross-owner/institutional write denial;
- design-authority preservation;
- authority-transfer denial;
- material-effect boundary;
- valid local owned-state mutation;
- idempotent replay and conflict denial;
- lease expiry and generation fencing;
- owner-scoped recovery and idempotency invalidation;
- stale state-version denial;
- restart preservation;
- durable Governor-contract revalidation;
- durable snapshot tamper detection;
- concurrent stale-writer fail-closed reconciliation;
- constructor-time binding substitution rejection.

This is engineering qualification by the implementation owner, not independent conformance or assurance.

## Hosted CI reservation

On QUALIFIED_CODE_HEAD, hosted GitHub Actions again failed before runner execution. Quality Gate run 34383704875 returned a failed job with `steps=null`. Therefore:

HOSTED_CI = PRE_RUNNER_FAILURE
HOSTED_CI_PASS = NOT_PROVEN
HOSTED_IMPLEMENTATION_TEST_FAILURE = NOT_DEMONSTRATED
LOCAL_TEST_EXECUTION = 24_PASSED

Local execution evidence does not convert hosted CI into PASS.

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

AGORA_ENGINEERING_QUALIFICATION = COMPLETE_FOR_INDEPENDENT_CONFORMANCE_REVIEW
NEXT_GATE = DÉDALA_CONFORMANCE
