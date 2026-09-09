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

## Qualification candidate

`tests/test_iris_v1_runtime.py` provides initial negative/positive qualification coverage for:

- six-binding construction gate;
- exact local derivation gate;
- local roster cardinality and anti-cloning;
- accessibility HOLD;
- evidence freshness non-promotion;
- cross-owner/institutional write denial;
- design-authority preservation;
- authority-transfer denial;
- material-effect boundary;
- valid local design-working mutation;
- lease expiry and generation fencing.

This implementation is a candidate. Test declarations are not evidence of execution until an execution environment runs them.

## Preserved reservations

RUNTIME_EFFECTIVENESS = NOT_ASSURED
ANATOMICAL_PARITY = UNPROVEN
DEEP_ANATOMICAL_PARITY_PROVEN = 0/10
ACCESSIBILITY_CONFLICT_NEGATIVE_RUNTIME_COVERAGE = IMPLEMENTED_AS_TEST_CANDIDATE_NOT_YET_EXECUTION_PROVEN
GLOBAL_FUNCTIONAL_PLENITUDE = NOT_PROVEN

EXECUTED != VERIFIED
VERIFIED != ASSURED
ASSURED != PROMOTED

MERGE = NOT_AUTHORIZED
CANONICAL_PROMOTION = NOT_AUTHORIZED
GOVERNOR_ACTIVATION = NOT_AUTHORIZED

NEXT_GATE = ÁGORA_ENGINEERING_QUALIFICATION_THEN_DÉDALA_CONFORMANCE
