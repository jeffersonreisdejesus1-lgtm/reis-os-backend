# Nóesis R7 Agentic Governance — Implementation 001

HANDOFF_ID = NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001
IMPLEMENTER = ÁGORA
BASE_MAIN = 063d42e745366a5315ec5bbb1cf433548d208150
CLASS = ADDITIVE_POST_REFACTOR_EVOLUTION
TARGET = NÓESIS
GENERATION = R7
STATUS = HOLD_WITH_REPAIRABLE_ARCHITECTURAL_RESERVATIONS

## Correct architectural boundary

R7 is NOT merely a layer above R1–R6.

R7 is an agentic governance domain embedded in, observed by and constrained by the
promoted R1–R6 physiology. L0 identity, authority and canonical state remain untouched.

Required causal relations:

- R1 -> persists R7 state;
- R2 -> measures R7 progress/effects;
- R3 -> types R7 transitions;
- R4 -> schedules R7 mechanisms;
- R7 -> executes specialized governance;
- R5 -> observes R7 plus the global chain;
- R6 -> constrains R7 plus the global chain.

The current candidate records these six relations as mandatory requirements while
tracking their implementation/evidence references separately. Presence of R1–R6 is
therefore not equivalent to proof of complete R1–R6 <-> R7 wiring.

Mandatory invariants:

- L0 binding hash remains `650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f`.
- IDI remains `REISOS::INST::NOESIS::001`.
- EC remains `EC-NOESIS-007`.
- exact active physiology is R1 through R6.
- `ORCHESTRATION != AUTHORITY`.
- `SCHEDULER != AUTHORITY`.
- `HANDOFF != AUTHORITY_TRANSFER`.
- `GOVERNOR != OCS`.
- `GOVERNOR_INFRASTRUCTURE != GOVERNOR_DERIVATION`.
- `GOVERNOR_CONTRACT != AUTHORITY_GRANT`.
- `R7_INTERNAL_GOVERNANCE != MATERIAL_EFFECT_EXECUTOR`.
- `BUILDER_ROLE != FINAL_ASSURANCE_ROLE`.

## Taxonomic freeze and Governor activation gate

Generic Governor mechanics are retained because they are reusable infrastructure.
Material Governor population is blocked by default.

`register_governor`, lease binding, scheduling, communication, execution and recovery
remain inert until ALL of the following are externally established by the Nóesis
architectural workstream:

- R7-I taxonomy frozen;
- R7-O taxonomy frozen;
- cross-taxonomy analysis complete;
- normalized requirements available;
- Governor derivation valid;
- a derivation reference is supplied.

Default behavior:

`GOVERNOR_ACTIVATION = DENY/HOLD`

Tests may use an explicitly labelled `synthetic-test-only` derivation fixture solely to
exercise generic mechanics. Such a fixture is not institutional evidence and cannot
promote a roster.

No final Governor roster is defined by this candidate. Functional interfaces STATE,
PROGRESS, TRANSITION, SCHEDULING, COMMUNICATION, LEASE, RECOVERY and EVIDENCE remain
implementation abstractions only.

## R1–R6 wiring status

The promoted physiology already materializes Blackboard, ProgressMonitor,
TypedTransition, PhysiologicalScheduler, TelemetryLedger and FormalChecks. Its
operational cycle is:

`BIND -> READ_STATE -> CLASSIFY -> SCHEDULE -> COGNITIVE_STEP -> MEASURE_DELTA -> PERSIST_STATE -> METHOD_CHANGE|HANDOFF|ESCALATE|STOP -> CHECK_GATE -> NEXT_CYCLE`

R7 must be reconciled into those mechanisms after Governor derivation defines the
actual R7 state, transition and observation surfaces.

Current material status:

- R1 state binding reference: PENDING;
- R2 measurement binding reference: PENDING;
- R3 transition binding reference: PENDING;
- R4 scheduler binding reference: PENDING;
- R5 observation binding reference: PENDING;
- R6 constraint binding reference: PENDING.

Therefore:

`FULL_R7_ARCHITECTURAL_CONFORMANCE = NOT_YET`

`R1_R6_PRESENCE != R1_R6_R7_WIRING_PROOF`

## Reusable candidate mechanics

The following candidate work is retained rather than discarded:

- generic Governor contracts;
- exclusive state ownership mechanics;
- scheduler admission mechanics;
- communication envelopes with authority-transfer prohibition;
- externally sourced leases;
- generation-aware fencing/recovery;
- idempotency and replay;
- rollback causal invalidation;
- receipt hash chain/readback;
- durable SQLite candidate snapshots with integrity and stale-writer fencing;
- failure injection tests;
- Effect Gate separation.

These mechanics are candidate infrastructure and do not constitute a Governor roster.

## Effect boundary

R7 internal mechanics do not execute external material effects.
`material_effect_requested=true` is denied. External effects require a separate Effect
Gate with independent authority, idempotency, execution receipt, reconciliation and
readback.

## Process boundary

Ágora is authorized to implement and repair this candidate under the exceptional
end-to-end implementation handoff. Ágora does not provide independent assurance over
its own implementation.

The next valid route is NOT Dédala yet. Architectural prerequisites return to Nóesis:

1. R7-I taxonomy;
2. R7-O taxonomy;
3. cross-taxonomy analysis;
4. normalized governance requirements;
5. Governor derivation.

After those artifacts exist, Ágora must:

1. reconcile the generic runtime with the legitimately derived roster;
2. complete concrete R1–R6 <-> R7 wiring and evidence references;
3. rerun engineering tests/failure injection;
4. regenerate the exact-head evidence package.

Only then:

`ÁGORA -> DÉDALA -> SÝNESIS -> FOUNDER_PROMOTION_GATE`

## Current disposition

GENERIC_R7_RUNTIME_MECHANICS = FUNCTIONAL_CANDIDATE
CURRENT_CODE_VALUE = HIGH_REUSABLE
REWRITE_REQUIRED = NO
TARGETED_CORRECTIONS = PARTIALLY_COMPLETED
GOVERNOR_ACTIVATION = BLOCKED_PENDING_DERIVATION
R7_I_TAXONOMY = PENDING_NOESIS
R7_O_TAXONOMY = PENDING_NOESIS
CROSS_TAXONOMY_ANALYSIS = PENDING_NOESIS
GOVERNOR_DERIVATION = PENDING_NOESIS
R1_R6_R7_WIRING = PENDING_POST_DERIVATION_RECONCILIATION
CONFORMANCE_PASS_ALLOWED = NO
PR79 = HOLD_CANDIDATE
CANONICAL_PROMOTION = NOT_AUTHORIZED
