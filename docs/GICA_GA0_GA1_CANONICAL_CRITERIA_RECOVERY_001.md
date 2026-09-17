# GICA — GA0/GA1 Canonical Criteria Recovery 001

OBJECT_ID: GICA-GA0-GA1-CANONICAL-CRITERIA-RECOVERY-001
PROGRAM: GICA / REIS OS
SOURCE_AUTHORITY: GICA-GA0-GA1-RETROSPECTIVE-REQUALIFICATION-ASSURANCE-001
CANONICAL_LEDGER: GICA-CANONICAL-PROGRAM-LEDGER-001
LEDGER_COMMIT: 3eaa0dbf2c584569419e0ceef5c4acd46eecd307
EARLIEST_RECOVERED_GICA_COMMIT: 92ddaf8a3716457bd27d57b71eb879fdf4423e70
CONTRACT_IMPLEMENTATION_COMMIT: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
ACCEPTANCE_TEST_COMMIT: baf6a41f37b385b4229eaf5360989f1c993aa87e
STATUS: CRITERIA_RECOVERED_AND_FROZEN_FOR_RETROSPECTIVE_REQUALIFICATION

## Scope rule

This artifact answers only: what can be recovered as the canonical executable criteria of GA0 and GA1?

It does not claim that GA0 or GA1 passed historically. Absence of a contemporaneous receipt is not a criterion of the new retrospective qualification.

Recovery classes:

- EXPLICIT: directly represented by code/test semantics.
- DETERMINISTICALLY_DERIVED: necessary consequence of explicit contract structure or gate name, without importing later gate requirements.
- UNRECOVERABLE: not sufficiently specified by surviving material and therefore excluded from executable PASS criteria unless separately recovered.

## Surviving canonical substrate

The recovered contract defines:

- GA0 = GA0_BOOTSTRAP.
- GA1 = GA1_SPECIFICATION_CONSISTENCY.
- GA2 = GA2_INDEPENDENT_ARCHITECTURAL_ASSURANCE.
- a fixed canonical roster of 11 unique OCS identities including TÊMIS;
- ACTIVE as the state required for gate advancement;
- strict sequential transitions GA0 -> GA1 -> GA2;
- valid authority as a prerequisite to every transition;
- complete gate evidence as a prerequisite to every transition;
- evidence resets to incomplete after a successful transition;
- invalid roster, inactive state, non-sequential transition, absent authority, or absent evidence fail closed through ProgramTransitionError.

The acceptance tests independently encode roster uniqueness, no gate skipping, authority requirement, evidence requirement and HOLD non-advancement. Their examples exercise GA3, but these transition predicates are implemented generically for every gate and therefore apply to GA0 and GA1 as deterministic consequences of the contract.

# GA0

GA0_PURPOSE: bootstrap a valid GICA program instance capable of entering GA1 under the canonical program contract.

GA0_PRECONDITIONS:
- a GicaProgramContract instance exists with a program_id;
- gate is GA0;
- program state is ACTIVE for advancement.

GA0_REQUIRED_ARTIFACTS:
- GicaProgramContract;
- GicaGate definition containing GA0 and GA1;
- CANONICAL_OCS_ROSTER.

GA0_REQUIRED_AUTHORITY:
- authority_bound = true before GA0 may transition to GA1.

GA0_REQUIRED_EVIDENCE:
- evidence_complete = true before GA0 may transition to GA1.
- the historical content schema of that evidence is not separately recoverable from the original contract and is not invented here.

GA0_INVARIANTS:
- canonical roster contains exactly 11 OCS identities;
- roster identities are unique;
- GA0 advancement is sequential only to GA1;
- program must be ACTIVE;
- authority is mandatory;
- evidence is mandatory;
- successful transition creates GA1 in ACTIVE state and resets evidence_complete to false.

GA0_HOLD_CONDITIONS:
- program state is not ACTIVE, including HOLD;
- required authority is absent;
- required gate evidence is absent;
- canonical roster validation fails;
- requested target is not GA1.

GA0_FAIL_CONDITIONS:
- deterministic violation of any mandatory contract invariant during qualification.

GA0_EXIT_CRITERIA:
- canonical roster validates;
- program is ACTIVE at GA0;
- authority_bound = true;
- evidence_complete = true;
- transition_to(GA1) succeeds;
- resulting contract is GA1/ACTIVE and evidence_complete = false.

## GA0_CANONICAL_CRITERIA

### GA0-C01
STATEMENT: GA0 exists as GA0_BOOTSTRAP and its only canonical successor is GA1.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: inspect GicaGate and _NEXT_GATE; execute GA0 -> GA1 and attempt a skipped target.
PASS_CONDITION: GA0 is defined and only GA1 is accepted as successor.
FAIL_CONDITION: GA0 missing, GA1 not its successor, or a non-sequential successor is accepted.

### GA0-C02
STATEMENT: the canonical OCS roster validates as exactly 11 unique identities including TÊMIS.
SOURCE: app/gica/contracts.py; tests/test_gica_ga4_slice_001_contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75; baf6a41f37b385b4229eaf5360989f1c993aa87e
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: call validate_roster and assert count, uniqueness and TÊMIS membership.
PASS_CONDITION: roster validation succeeds with exactly 11 unique identities including TÊMIS.
FAIL_CONDITION: count/uniqueness/membership contract fails.

### GA0-C03
STATEMENT: GA0 may advance only while program state is ACTIVE.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute transition from ACTIVE and from HOLD/non-ACTIVE state.
PASS_CONDITION: ACTIVE is eligible subject to remaining predicates and non-ACTIVE is denied.
FAIL_CONDITION: a non-ACTIVE GA0 advances.

### GA0-C04
STATEMENT: valid bound authority is mandatory for GA0 -> GA1.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute GA0 -> GA1 with authority_bound true and false.
PASS_CONDITION: false is denied with valid_authority_required; true may proceed subject to other predicates.
FAIL_CONDITION: transition succeeds without bound authority.

### GA0-C05
STATEMENT: complete gate evidence is mandatory for GA0 -> GA1.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute GA0 -> GA1 with evidence_complete true and false.
PASS_CONDITION: false is denied with gate_evidence_required; true may proceed subject to other predicates.
FAIL_CONDITION: transition succeeds without complete gate evidence.

### GA0-C06
STATEMENT: successful GA0 -> GA1 preserves bound authority, enters ACTIVE GA1 and resets evidence_complete to false.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute a valid GA0 -> GA1 transition and inspect result.
PASS_CONDITION: gate=GA1, state=ACTIVE, authority remains bound, evidence_complete=false.
FAIL_CONDITION: resulting state violates any listed postcondition.

# GA1

GA1_PURPOSE: establish specification-consistency readiness sufficient to permit entry into GA2 under the canonical program contract.

GA1_PRECONDITIONS:
- a valid GicaProgramContract is at GA1;
- program state is ACTIVE for advancement;
- GA1 is reached through the sequential gate model.

GA1_REQUIRED_ARTIFACTS:
- GicaProgramContract;
- GicaGate definition containing GA1 and GA2;
- CANONICAL_OCS_ROSTER.

GA1_REQUIRED_AUTHORITY:
- authority_bound = true before GA1 may transition to GA2.

GA1_REQUIRED_EVIDENCE:
- evidence_complete = true before GA1 may transition to GA2.
- a distinct original schema defining the substantive contents of "specification consistency" was not recovered from the surviving initial contract; no additional schema is fabricated.

GA1_INVARIANTS:
- canonical roster remains valid;
- GA1 advancement is sequential only to GA2;
- program must be ACTIVE;
- authority is mandatory;
- evidence is mandatory;
- successful transition creates GA2 in ACTIVE state and resets evidence_complete to false.

GA1_HOLD_CONDITIONS:
- program state is not ACTIVE, including HOLD;
- required authority is absent;
- required gate evidence is absent;
- canonical roster validation fails;
- requested target is not GA2.

GA1_FAIL_CONDITIONS:
- deterministic violation of any mandatory contract invariant during qualification.

GA1_EXIT_CRITERIA:
- canonical roster validates;
- program is ACTIVE at GA1;
- authority_bound = true;
- evidence_complete = true;
- transition_to(GA2) succeeds;
- resulting contract is GA2/ACTIVE and evidence_complete = false.

## GA1_CANONICAL_CRITERIA

### GA1-C01
STATEMENT: GA1 exists as GA1_SPECIFICATION_CONSISTENCY and its only canonical successor is GA2.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: inspect GicaGate and _NEXT_GATE; execute GA1 -> GA2 and attempt a skipped target.
PASS_CONDITION: GA1 is defined and only GA2 is accepted as successor.
FAIL_CONDITION: GA1 missing, GA2 not its successor, or a non-sequential successor is accepted.

### GA1-C02
STATEMENT: the canonical 11-OCS roster remains a mandatory valid invariant at GA1.
SOURCE: app/gica/contracts.py; tests/test_gica_ga4_slice_001_contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75; baf6a41f37b385b4229eaf5360989f1c993aa87e
RECOVERY_CLASS: DETERMINISTICALLY_DERIVED
TEST_METHOD: validate roster on a GA1 contract before transition.
PASS_CONDITION: exactly 11 unique identities including TÊMIS and validate_roster succeeds.
FAIL_CONDITION: roster invariant fails.

### GA1-C03
STATEMENT: GA1 may advance only while program state is ACTIVE.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute GA1 -> GA2 from ACTIVE and non-ACTIVE states.
PASS_CONDITION: non-ACTIVE is denied and ACTIVE remains eligible subject to other predicates.
FAIL_CONDITION: non-ACTIVE GA1 advances.

### GA1-C04
STATEMENT: valid bound authority is mandatory for GA1 -> GA2.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute GA1 -> GA2 with authority_bound true and false.
PASS_CONDITION: false is denied with valid_authority_required.
FAIL_CONDITION: GA1 advances without bound authority.

### GA1-C05
STATEMENT: complete gate evidence is mandatory for GA1 -> GA2.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute GA1 -> GA2 with evidence_complete true and false.
PASS_CONDITION: false is denied with gate_evidence_required.
FAIL_CONDITION: GA1 advances without complete gate evidence.

### GA1-C06
STATEMENT: successful GA1 -> GA2 preserves bound authority, enters ACTIVE GA2 and resets evidence_complete to false.
SOURCE: app/gica/contracts.py
SOURCE_HEAD: 94c341d023fa887ac0a0da9df3d1aa31c466bb75
RECOVERY_CLASS: EXPLICIT
TEST_METHOD: execute a valid GA1 -> GA2 transition and inspect result.
PASS_CONDITION: gate=GA2, state=ACTIVE, authority remains bound, evidence_complete=false.
FAIL_CONDITION: resulting state violates any listed postcondition.

## Explicitly unrecovered semantics

The surviving initial contract names GA1 as SPECIFICATION_CONSISTENCY but does not encode a separate field-level schema for the substantive contents of specification consistency beyond the common gate predicates. Therefore the following is frozen as:

GA1-SUBSTANTIVE-SPECIFICATION-SCHEMA = CANONICAL_CRITERION_UNRECOVERABLE

This unrecovered detail is not silently promoted into a new requirement and is not converted into historical FAIL. ÁGORA must report whether this missing semantic detail is material to a present-day retrospective decision.

Likewise, the initial contract does not encode a distinct content schema for GA0's evidence payload beyond evidence_complete. Therefore:

GA0-EVIDENCE-CONTENT-SCHEMA = CANONICAL_CRITERION_UNRECOVERABLE

## Frozen requalification interface

ÁGORA shall execute GA0-C01..C06 and GA1-C01..C06 against the bound present-day candidate and separately assess the two unrecovered semantic items.

Allowed outcomes per gate:

- RETROSPECTIVELY_QUALIFIABLE
- HOLD
- FAIL

Historical PASS remains prohibited regardless of outcome.

NEXT_HANDOFF: NOESIS-TO-AGORA-GICA-GA0-GA1-CURRENT-DATE-REQUALIFICATION-001
