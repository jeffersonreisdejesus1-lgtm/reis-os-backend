# CUPUWA Skill Acquisition — Contract

HANDOFF_ID = NOESIS-TO-SOFIA-CUPUWA-SKILL-ACQUISITION-IMPLEMENTATION-001
PROGRAM = REIS OS / CUPUWA
PROCEDURE = CUPUWA-SKILL-ACQUISITION-001
BRANCH = cupuwa/skill-acquisition-001
BASE_HEAD = c181630ebab0f0929cd58626a608b8290491080a

## Objective

Materialize the governed lifecycle for a missing Skill without allowing an
OCS, a model, a capability, or a receipt to register authority or silently
create institutional knowledge.

## Required lifecycle

Mission
→ capability resolution
→ Skill Registry lookup
→ NOT_FOUND
→ SkillCandidate
→ evidence collection
→ independent validation
→ registration
→ later discovery

## Required behavior

- A missing Skill produces an explicit NOT_FOUND result.
- The system may create a candidate, never an automatically validated Skill.
- Candidate identity and version are deterministic.
- Candidate provenance records proposer, capability, procedure, evidence, and
  status.
- Candidate status is CANDIDATE until independent validation.
- CANDIDATE entries cannot be loaded or executed.
- Registration requires an independent validation decision.
- Conflicting candidate payloads fail closed.
- A registered Skill must preserve Skill != Authority.
- A receipt must distinguish discovery, proposal, validation, and registration.
- No authority is granted by candidate creation or registration.

## Acceptance tests

1. Missing capability returns NOT_FOUND.
2. Candidate creation is deterministic.
3. Candidate status is CANDIDATE.
4. Candidate cannot be loaded.
5. Candidate evidence is preserved.
6. Duplicate identical candidate is idempotent.
7. Conflicting candidate payload fails closed.
8. Registration without validation is rejected.
9. Validated registration becomes discoverable.
10. Registered Skill still has authority_granted = NONE.
11. Candidate and registration receipts are distinguishable.
12. Existing Skills Foundation and Enforcement suites remain passing.

## Explicit non-goals

- automatic learning without validation;
- automatic authority expansion;
- external agent dispatch;
- universal proof of the 72 OCSs;
- merge or promotion.

## Responsibility

SOFIA: implement this acquisition boundary.
ÁGORA: qualify candidate lifecycle and registration controls.
SÝNESIS: assure provenance and authority separation when requested.
NÓESIS: reconcile and close the increment.

NO_AUTHORITY_EXPANSION = TRUE
NO_SILENT_REGISTRATION = TRUE
NO_EXECUTION_OF_CANDIDATE = TRUE
NO_EXTERNAL_DISPATCH = TRUE
NO_MERGE = TRUE
NO_PROMOTION = TRUE
