# Nóesis R7 Agentic Governance — Implementation 001

HANDOFF_ID = NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001
IMPLEMENTER = ÁGORA
BASE_MAIN = 063d42e745366a5315ec5bbb1cf433548d208150
CLASS = ADDITIVE_POST_REFACTOR_EVOLUTION
TARGET = NÓESIS
GENERATION = R7
STATUS = IMPLEMENTATION_RECONCILED_FOR_ADVERSARIAL_REVIEW

R7 is an agentic governance domain embedded in, observed by and constrained by the promoted R1–R6 physiology. L0 identity, authority and canonical state remain untouched.

DERIVATION_REF = NOESIS-R7-GOVERNOR-ROSTER-DERIVATION-001
DERIVED_ROSTER = 17_CANDIDATE_GOVERNORS
ROSTER_SIZE = DERIVED_PROPERTY
DESIGN_TARGET = FALSE

Internal R7-I: A-CTX, A-CG, A-MEM-WORKING, A-MEM-DURABLE, A-DTRUST, A-EVID, A-LEARN, A-HOME, A-RECOVERY, A-PI-ORCH.

Outer R7-O: OG-INTAKE, OG-ORCH-ROUTE, OG-HANDOFF, OG-PROGRAM-STATE, OG-EVOLUTION, OG-AUTH, OG-RUNTIME.

A-EXEC = REJECTED_AS_R7_GOVERNOR

Mandatory boundaries remain:

- ORCHESTRATION != AUTHORITY
- SCHEDULER != AUTHORITY
- HANDOFF != AUTHORITY_TRANSFER
- HANDOFF != IDENTITY_TRANSFER
- GOVERNOR != OCS
- GOVERNOR_CONTRACT != AUTHORITY_GRANT
- R7_INTERNAL_GOVERNANCE != MATERIAL_EFFECT_EXECUTOR
- BUILDER_ROLE != FINAL_ASSURANCE_ROLE

The six concrete R1–R6 bridge references are materialized in `app/noesis_r7/physiology_bindings.py` and tracked independently in the R1–R6 integration contract.

Direct runtime registration is constrained by the derived roster. `R7GovernanceRuntime.register_governor()` validates the requested Governor ID against the exact derived roster using the architectural readiness derivation reference. A raw `GovernorContract` therefore cannot bypass the roster gate.

DIRECT_REGISTER_ROSTER_BYPASS = CLOSED_BY_IMPLEMENTATION

The qualification specification covers exact 17-Governor cardinality, uniqueness, 10/7 split, rejection of A-EXEC, exact derivation reference, six distinct R1–R6 binding refs, direct runtime rejection of non-derived Governors, plus scheduler/authority/state ownership/generation/recovery/rollback/idempotency/durability/tamper/stale-writer/crash-recovery cases.

Hosted CI is not represented as PASS. GitHub Actions continues to fail before runner execution (`steps=null`).

HOSTED_CI = PRE_RUNNER_FAILURE
HOSTED_CI_PASS = NOT_CLAIMED
IMPLEMENTATION_TEST_FAILURE = NOT_DEMONSTRATED_BY_HOSTED_CI

No merge, promotion, production or Governor institutional activation is performed here.

AGORA_IMPLEMENTATION = COMPLETE_FOR_REVIEW
AGORA_SELF_ASSURANCE = FORBIDDEN
PR79 = CANDIDATE_FOR_DEDALA_REVIEW
CANONICAL_PROMOTION = NOT_AUTHORIZED

Next route:

ÁGORA -> DÉDALA -> [ÁGORA_REPAIR <-> DÉDALA_REVIEW]* -> SÝNESIS -> FOUNDER_PROMOTION_GATE

Implementation findings return to Ágora. Architectural findings return to Nóesis.
