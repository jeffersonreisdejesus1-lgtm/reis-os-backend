# CUPUWA Skill Receipt Runtime Binding

HANDOFF_ID = NOESIS-TO-SOFIA-CUPUWA-SKILL-RECEIPT-RUNTIME-BINDING-IMPLEMENTATION-001
PROGRAM = REIS OS / CUPUWA
PROCEDURE = CUPUWA-SKILL-RECEIPT-RUNTIME-BINDING-001
BRANCH = cupuwa/skill-receipt-runtime-binding-001
BASE_HEAD = d18f01d47b0ae46d71d459391202b59ab73fda43

## Objective

Bind every enforced local Skill execution to durable SkillReceipt persistence and
readback before success is returned.

## Required path

enforcement
→ local executor
→ SkillReceipt
→ durable store
→ readback
→ mission result

## Required behavior

- persistence is mandatory when the runtime is configured for durable receipts;
- operation_id is stable and capability-specific;
- replay reads the canonical receipt before executing again;
- conflicting payloads fail closed;
- failed persistence prevents a success claim;
- receipt authority_ref is preserved, never minted;
- foundation, enforcement, acquisition, and store semantics remain intact.

## Acceptance

- first execution persists and reads back the receipt;
- identical replay returns the canonical persisted receipt;
- replay does not execute the procedure again;
- conflicting replay fails closed;
- persistence failure prevents success;
- restart recovers the receipt;
- legacy non-durable calls remain explicitly supported only when the store is
  absent and the caller has selected non-durable mode.

NO_AUTHORITY_EXPANSION = TRUE
NO_BLIND_REPLAY = TRUE
NO_FALSE_SUCCESS = TRUE
NO_EXTERNAL_DISPATCH = TRUE
NO_MERGE = TRUE
NO_PROMOTION = TRUE
