# Nóesis Layered Physiology Refactor 001

MISSION = NOESIS-LAYERED-PHYSIOLOGY-REFACTOR-001
STATUS = NONCANONICAL_CANDIDATE
BASE_CANONICAL_EC = EC-NOESIS-007
BASE_PACKAGE = NOESIS_NATIVE_EC007_20260823_v0.2.1.zip
BASE_PACKAGE_SHA256 = 691d738823b52265af6a268a287e3475e446a4b7f3aaec681856b3f27cdcd06c
BASE_L0_BINDING_HASH = 650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f
CANDIDATE_PACKAGE = NOESIS_NATIVE_EC007_LAYERED_REFACTOR_CANDIDATE_20260908_v0.3.0.zip
CANDIDATE_PACKAGE_SHA256 = 55fab30eb97289b8f1c977b9d63c8c07d08d97a4d015dcfde8fc9dc3ac706f14

## Architectural rule

NÓESIS_CURRENT = canonical L0.

NÓESIS_REFACTORED_CANDIDATE = same untouched L0 + additive physiological mechanism layers.

The ancestral `Noesis` identity, binding, canonical EC, governance, authority, functional heritage F01–F24, single native physiology and authoritative state root are not rewritten by this candidate.

`L1..L6 MAY CONTROL MECHANISM`

`L1..L6 MUST NOT ALTER IDENTITY`

`ORCHESTRATION != AUTHORITY`

`HANDOFF != AUTHORITY_TRANSFER`

## Staged architecture

R1 — EXPLICIT_STATE / BLACKBOARD

R2 — PROGRESS_MONITOR

R3 — TYPED_TRANSITIONS

R4 — SCHEDULER

R5 — TELEMETRY

R6 — FORMAL_RUNTIME_CHECKS

Every stage is cumulatively activatable and can be capped independently so empirical comparisons retain causal attribution.

## Operational cycle

`BIND -> READ_STATE -> CLASSIFY -> SCHEDULE -> COGNITIVE_STEP -> MEASURE_DELTA -> PERSIST_STATE -> METHOD_CHANGE|HANDOFF|ESCALATE|STOP -> CHECK_GATE -> NEXT_CYCLE`

The cognitive step remains the native Nóesis cognitive engine. The layered physiology constrains and observes mechanism around it.

## Blackboard minimum state

- MISSION_ID
- CURRENT_OBJECT
- CURRENT_PHASE
- CURRENT_ACTOR
- LAST_ACTION
- LAST_MATERIAL_DELTA
- OPEN_FINDINGS
- BLOCKERS
- PENDING_GATES
- AUTHORIZED_NEXT_ACTORS
- PROHIBITED_TRANSITIONS
- STOP_CONDITIONS
- DECISIONS
- EVIDENCE_REFS
- VERIFIED_CLAIMS
- STAGNATION_CYCLES
- STOPPED / STOP_REASON
- CYCLE

## Material progress

The progress monitor measures delta across evidence, phase/state, findings, blockers, decisions and verified claims. When there is no material delta for the configured bound, Nóesis cannot simply continue thinking indefinitely; the mechanism must choose an allowed `METHOD_CHANGE`, typed handoff, escalation or explicit stop.

## Typed relations

Examples:

`NOESIS --HANDOFF_FOR_CONFORMANCE--> DEDALA`

`DEDALA --RETURNS_FINDING_TO--> NOESIS`

`NOESIS --ESCALATE_TO_FOUNDER--> FOUNDER`

Every handoff explicitly sets `authority_transferred = false`.

## Scheduler boundary

The scheduler determines which mechanism transitions are admissible for the current phase. It never grants institutional authority.

Always prohibited in this candidate:

- SELF_ASSURANCE
- SELF_PROMOTION
- CREATE_AUTHORITY
- BYPASS_FOUNDER_GATE
- CANONICAL_WRITE
- PRODUCTION
- MERGE

A request containing a forbidden transition is blocked before the native cognitive step.

## Telemetry

Each observable cycle may record cycle, actor, state before, action, reason, material delta, gate, state after and a hash-chain predecessor/event digest.

## Formal runtime checks

R6 checks at runtime that:

- L0 binding hash is unchanged;
- IDI remains `REISOS::INST::NOESIS::001`;
- current EC remains `EC-NOESIS-007`;
- scheduler did not grant forbidden authority;
- stopped state has an explicit stop reason;
- telemetry chain verifies.

## Qualification boundary

The candidate was built additively from the exact recoverable canonical package and replayed from a fresh extraction. The original Drive package was not mutated or overwritten.

This artifact does not authorize canonical promotion, production, adoption, self-assurance, universal rollout or merge.