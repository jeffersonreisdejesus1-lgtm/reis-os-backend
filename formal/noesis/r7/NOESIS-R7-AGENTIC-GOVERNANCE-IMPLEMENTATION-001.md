# Nóesis R7 Agentic Governance — Implementation 001

HANDOFF_ID = NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001
IMPLEMENTER = ÁGORA
BASE_MAIN = 063d42e745366a5315ec5bbb1cf433548d208150
CLASS = ADDITIVE_POST_REFACTOR_EVOLUTION
TARGET = NÓESIS
GENERATION = R7
STATUS = IMPLEMENTATION_RECONCILED_FOR_ADVERSARIAL_REVIEW

## Architectural boundary

R7 is an agentic governance domain embedded in, observed by and constrained by the promoted R1–R6 physiology. L0 identity, authority and canonical state remain untouched.

Required causal relations are materialized as explicit bridge functions:

- R1 -> persists R7 state;
- R2 -> measures R7 progress/effects;
- R3 -> types R7 transitions;
- R4 -> schedules R7 mechanisms;
- R7 -> executes specialized governance;
- R5 -> observes R7 plus the global chain;
- R6 -> constrains R7 plus the global chain.

Mandatory invariants:

- L0 binding hash remains `650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f`.
- IDI remains `REISOS::INST::NOESIS::001`.
- EC remains `EC-NOESIS-007`.
- exact active physiology is R1 through R6.
- `ORCHESTRATION != AUTHORITY`.
- `SCHEDULER != AUTHORITY`.
- `HANDOFF != AUTHORITY_TRANSFER`.
- `HANDOFF != IDENTITY_TRANSFER`.
- `GOVERNOR != OCS`.
- `GOVERNOR_CONTRACT != AUTHORITY_GRANT`.
- `R7_INTERNAL_GOVERNANCE != MATERIAL_EFFECT_EXECUTOR`.
- `BUILDER_ROLE != FINAL_ASSURANCE_ROLE`.

## Derived roster

`DERIVATION_REF = NOESIS-R7-GOVERNOR-ROSTER-DERIVATION-001`

Roster cardinality is a derived property, not a design target.

Internal R7-I: A-CTX, A-CG, A-MEM-WORKING, A-MEM-DURABLE, A-DTRUST, A-EVID, A-LEARN, A-HOME, A-RECOVERY, A-PI-ORCH.

Outer R7-O: OG-INTAKE, OG-ORCH-ROUTE, OG-HANDOFF, OG-PROGRAM-STATE, OG-EVOLUTION, OG-AUTH, OG-RUNTIME.

`A-EXEC` is explicitly rejected as an R7 Governor. Memory remains split between working and durable lifecycles. Institutional orchestration and OCS routing remain merged. Authority/scope and runtime lifecycle governance remain separate.

## Activation and registration gate

Governor activation remains fail-closed unless all architectural readiness conditions are true and the exact derivation reference is present.

Direct runtime registration is constrained by the derived roster. `register_governor()` validates the requested Governor ID against the canonical derived roster using the readiness derivation reference. A raw `GovernorContract` cannot bypass the roster gate.

`DIRECT_REGISTER_ROSTER_BYPASS = CLOSED_BY_IMPLEMENTATION`

`GOVERNOR_ACTIVATION != INSTITUTIONAL_PROMOTION`

## R1–R6 wiring

The six concrete bridge references are materialized in `app/noesis_r7/physiology_bindings.py` and tracked independently in the R1–R6 integration contract.

The promoted physiology remains the constraining substrate: R1 explicit state blackboard; R2 progress monitor; R3 typed transitions; R4 physiological scheduler; R5 telemetry ledger; R6 formal checks.

`R1_R6_PRESENCE != R1_R6_R7_WIRING_PROOF`; this candidate carries explicit wiring references rather than inferring integration from layer presence.

## Qualification surface

Qualification specification covers exact 17-Governor cardinality, uniqueness, 10/7 split, rejection of A-EXEC, exact derivation reference, six distinct R1–R6 binding refs, direct runtime registration rejection of non-derived Governors, and the existing scheduler/authority/state ownership/generation/recovery/rollback/idempotency/durability/tamper/stale-writer/crash-recovery cases.

Hosted CI is not represented as PASS. GitHub Actions continues to fail before runner execution (`steps=null` / no test steps).

`HOSTED_CI = PRE_RUNNER_FAILURE`

`HOSTED_CI_PASS = NOT_CLAIMED`

`IMPLEMENTATION_TEST_FAILURE = NOT_DEMONSTRATED_BY_HOSTED_CI`

## Process boundary

Ágora implemented and repaired this candidate under the end-to-end implementation handoff. Ágora does not provide independent assurance over its own implementation.

No merge, promotion, production or Governor institutional activation is performed by this document.

Next route:

`ÁGORA -> DÉDALA -> [ÁGORA_REPAIR <-> DÉDALA_REVIEW]* -> SÝNESIS -> FOUNDER_PROMOTION_GATE`

Implementation findings return to Ágora. Architectural findings return to Nóesis.

## Current disposition

R7_I_TAXONOMY = FROZEN
R7_O_TAXONOMY = FROZEN
CROSS_TAXONOMY_ANALYSIS = COMPLETE
GOVERNOR_DERIVATION = VALID
DERIVED_ROSTER = 17_CANDIDATE_GOVERNORS
R1_R6_R7_WIRING = MATERIALIZED_WITH_EXPLICIT_BINDING_REFS
DIRECT_REGISTER_ROSTER_ENFORCEMENT = MATERIALIZED
QUALIFICATION_SPEC = REGENERATED
HOSTED_CI = PRE_RUNNER_FAILURE
HOSTED_CI_PASS = NOT_CLAIMED
AGORA_IMPLEMENTATION = COMPLETE_FOR_REVIEW
PR79 = CANDIDATE_FOR_DEDALA_REVIEW
CANONICAL_PROMOTION = NOT_AUTHORIZED
