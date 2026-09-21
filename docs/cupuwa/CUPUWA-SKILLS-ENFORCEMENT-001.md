# CUPUWA Skills Enforcement — Contract

HANDOFF_ID = NOESIS-TO-SOFIA-CUPUWA-SKILLS-ENFORCEMENT-IMPLEMENTATION-001
PROGRAM = REIS OS / CUPUWA
PROCEDURE = CUPUWA-SKILLS-ENFORCEMENT-001
BRANCH = cupuwa/skills-enforcement-001
BASE_HEAD = 581b159e5099d80b5f3519faa7dca40bb6ce3ab9

## Objective

Make Skill discovery and authorization an enforced runtime boundary for
missions that declare a required capability.

A mission requiring a capability must not reach an executor through an
alternate path that bypasses Skill Registry, resolution, loading, and the
authority check.

## Required path

Mission
→ authority validation
→ capability validation
→ Skill Registry resolution
→ Skill loading
→ executor
→ receipt

## Required behavior

- A mission with required capabilities must resolve every required capability.
- Missing, ambiguous, retired, or unavailable Skills fail closed.
- A direct executor call without a resolved Skill must be rejected.
- A Skill cannot create or expand authority.
- Optional capabilities must be explicitly marked optional; omission cannot be
  silently treated as success.
- The enforcement decision must produce a deterministic receipt or a
  deterministic rejection.
- The existing Skills Foundation semantics must remain unchanged.
- No external worker dispatch is part of this procedure.

## Acceptance tests

1. Required capability with validated Skill reaches the executor.
2. Required capability without Skill is rejected.
3. Ambiguous Skill resolution is rejected.
4. Retired Skill is rejected.
5. Direct executor invocation without Skill binding is rejected.
6. Missing authority is rejected before resolution.
7. Capability outside the mission is rejected.
8. Repeated enforcement for the same mission/capability is deterministic.
9. Receipt distinguishes resolved, rejected, and executed states.
10. Existing foundation tests remain passing.

## Boundaries

This procedure does not prove:

- external agent or worker execution;
- distributed execution;
- durable receipt persistence;
- automatic Skill acquisition;
- operation of all 72 OCSs;
- merge or promotion.

## Responsibility

SOFIA: implement only this enforcement slice.
ÁGORA: qualify the resulting HEAD independently.
SÝNESIS: perform assurance after qualification, if requested.
NÓESIS: reconcile and close the increment.

NO_AUTHORITY_EXPANSION = TRUE
NO_EXTERNAL_DISPATCH = TRUE
NO_FOUNDATION_REWRITE = TRUE
NO_MERGE = TRUE
NO_PROMOTION = TRUE
