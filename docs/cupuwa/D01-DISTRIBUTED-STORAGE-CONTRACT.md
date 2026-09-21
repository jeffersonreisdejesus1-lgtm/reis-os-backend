# D01 — Distributed Storage Contract

Status: CONTRACT_DEFINED / IMPLEMENTATION_NOT_STARTED

## Canonical identity

Every distributed record is keyed by:

- mission_id
- operation_id
- payload_fingerprint
- schema_version

operation_id is the canonical operation identity. mission_id is causal context and
must not replace operation_id.

## Required states

ABSENT -> PENDING -> EXECUTING -> SUCCEEDED | FAILED | UNKNOWN
UNKNOWN -> RECONCILING -> RECONCILED | HOLD

UNKNOWN is not success and is not permission for blind retry.

## Consistency rules

- identical operation_id and payload returns the canonical existing record;
- identical operation_id with a different payload fails closed;
- at most one active owner exists for an operation;
- stale owners cannot complete or overwrite a newer claim;
- a success claim requires a durable receipt and coherent readback;
- missing or corrupt readback yields HOLD;
- authority references are preserved, never minted by storage;
- storage records are evidence/state, not authority or promotion.

## Distributed proof required later

D01 does not prove distribution. D02-D06 must demonstrate:

- independent process or host access;
- durable ownership/lease;
- restart and host-loss recovery;
- reconciliation after uncertain writes;
- deterministic replay;
- receipt integrity;
- failure without false success.

## Boundary

The existing local Skill receipt store remains closed and unchanged.
No external service, worker, Orchestrator, merge, promotion, or product effect
is introduced by D01.
