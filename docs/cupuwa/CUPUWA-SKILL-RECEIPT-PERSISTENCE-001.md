# CUPUWA Skill Receipt Persistence — Contract

HANDOFF_ID = NOESIS-TO-SOFIA-CUPUWA-SKILL-RECEIPT-PERSISTENCE-IMPLEMENTATION-001
PROGRAM = REIS OS / CUPUWA
PROCEDURE = CUPUWA-SKILL-RECEIPT-PERSISTENCE-001
BRANCH = cupuwa/skill-receipt-persistence-001
BASE_HEAD = e876ec1aba2e0c5782eafd1782d74ccb6ea2e650

## Objective

Persist Skill execution receipts durably and recover them after restart while
preserving operation identity, deterministic replay, and fail-closed behavior.

## Required lifecycle

Skill execution
→ receipt creation
→ durable write
→ readback verification
→ restart
→ canonical receipt recovery

## Required behavior

- Receipt identity is deterministic for the same mission, Skill, authority
  reference, payload/result digest, and operation identity.
- Writing the same receipt twice is idempotent.
- Conflicting payload or result for the same operation fails closed.
- Restart/readback returns the canonical receipt.
- Corrupt or incomplete receipts are rejected.
- Missing readback prevents a success claim.
- Receipt persistence never grants or expands authority.
- Receipt is evidence, not assurance or promotion.
- The existing Skill, enforcement, and acquisition semantics remain unchanged.

## Acceptance tests

1. Persist a successful SkillReceipt.
2. Read it back after reopening storage.
3. Replay returns the same receipt.
4. Conflicting replay fails closed.
5. Corrupted receipt is rejected.
6. Missing receipt prevents success claim.
7. Receipt hash is deterministic.
8. Authority reference is preserved, not created.
9. Proposal/validation receipts remain distinguishable from execution receipts.
10. Existing foundation, enforcement, and acquisition suites remain passing.

## Non-goals

- external worker dispatch;
- distributed storage;
- cryptographic authority validation;
- automatic promotion;
- merge.

NO_AUTHORITY_EXPANSION = TRUE
NO_FALSE_SUCCESS = TRUE
NO_BLIND_REPLAY = TRUE
NO_EXTERNAL_DISPATCH = TRUE
NO_MERGE = TRUE
NO_PROMOTION = TRUE
