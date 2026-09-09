# Nóesis R7 Agentic Governance — Implementation 001

HANDOFF_ID = NOESIS-TO-AGORA-R7-REFACTOR-IMPLEMENTATION-001
IMPLEMENTER = ÁGORA
BASE_MAIN = 063d42e745366a5315ec5bbb1cf433548d208150
CLASS = ADDITIVE_POST_REFACTOR_EVOLUTION
TARGET = NÓESIS
GENERATION = R7

## Boundary

R7 is an internal governance runtime layered above the promoted R1–R6 physiology.
It does not rewrite L0, identity, current EC, R1–R6 state semantics, Founder authority,
or the external cognitive ecology.

Mandatory invariants:

- L0 binding hash remains `650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f`.
- IDI remains `REISOS::INST::NOESIS::001`.
- EC remains `EC-NOESIS-007`.
- exact active physiology is R1 through R6.
- `ORCHESTRATION != AUTHORITY`.
- `SCHEDULER != AUTHORITY`.
- `HANDOFF != AUTHORITY_TRANSFER`.
- `GOVERNOR != OCS`.
- `GOVERNOR_CONTRACT != AUTHORITY_GRANT`.
- `R7_INTERNAL_GOVERNANCE != MATERIAL_EFFECT_EXECUTOR`.
- `BUILDER_ROLE != FINAL_ASSURANCE_ROLE`.

## Governor model

This implementation deliberately freezes a **Governor contract model**, not a final
Governor identity roster. A Governor is a mission-bound functional controller with:

- governor_id;
- functional interface;
- exclusive owned state keys;
- readable state keys;
- allowed internal command classes;
- authority ceiling reference;
- mandatory lease policy;
- generational recovery policy.

Functional interfaces currently represent STATE, PROGRESS, TRANSITION, SCHEDULING,
COMMUNICATION, LEASE, RECOVERY and EVIDENCE. These are interfaces, not new OCSs and
not a claim that the final institutional roster must contain exactly eight Governors.

## State ownership

No two registered Governors may own the same state key. A command can mutate only
keys owned by its Governor contract. Cross-owner writes fail closed before state
commit and report `mutation_count = 0`.

R7 state is subordinate runtime state. It is not a new canonical institutional root.

## Scheduling

Tasks are ordered deterministically by priority, then creation sequence, then task ID.
The scheduler can select only command classes already admitted by a Governor contract.
Forbidden authority actions remain blocked even if a malformed contract lists them.

## Communication

Governor communication uses typed envelopes with source, receiver, mission, relation
and payload reference. `authority_transferred=true` is structurally rejected.

## Lease and fencing

Every mutable command requires a lease bound to:

- governor;
- mission;
- authority reference;
- scope;
- generation;
- validity window;
- max uses.

Expired, exhausted, foreign, fenced or stale-generation leases fail closed.
Replacement/recovery fences every lease of the predecessor generation before the
next generation is considered current.

## Effect boundary

R7 executes governed internal state commits only. `material_effect_requested=true`
is denied even with a valid lease. External material effects require a later effect
gate with separate authority, idempotency, reconciliation, execution receipt and
readback.

## Idempotency and reconciliation

The exact same command under the same idempotency key replays without another state
mutation. Same key with a divergent command fingerprint is a hard conflict.

Failure after commit is recoverable by exact replay: the committed receipt and
idempotency record prevent duplicate state effect.

## Recovery

Checkpoint captures mission, generation, state version, governed state and the
predecessor receipt hash. Recovery performs:

`FENCE_PREDECESSOR -> ADVANCE_GENERATION -> RESTORE_CHECKPOINT`

An old-generation command is denied after recovery.

## Rollback

`rollback_to_checkpoint` applies only to internal R7 governed state. It makes no claim
that an already performed external material effect can be rolled back. External-effect
rollback requires its own effect-specific recovery contract and evidence.

## Evidence

R7 receipts contain state versions before/after, mutation count, material-effect flag,
readback values and a predecessor hash. Receipt integrity is hash chained.

## Failure injection

The engineering test matrix includes failures:

- after validation;
- before commit;
- after commit.

Pre-commit failure must preserve state/version and emit no successful receipt.
Post-commit failure must converge through idempotent replay without duplicate commit.

## Promotion boundary

This branch is an implementation candidate only.

Ágora may implement, test, repair and package evidence under the current handoff.
Dédala performs the next adversarial technical review. Sýnesis remains independent
institutional assurance. Canonical promotion remains Founder-reserved.
