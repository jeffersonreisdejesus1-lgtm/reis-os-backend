# IB9 H-06 — Authoritative Binding Reconciliation

## Scope

This slice narrows the PR to the IB9 H-06 authoritative binding/reconciliation boundary:

InstanceBindingStore -> OCSInstanceBinder -> OCSInstanceRecovery -> HazelBoundContinuity

The runtime composes existing local binding/recovery services. WorkInstanceBridge accepts only an externally produced WorkSpawnReceipt; it does not spawn Work. CommandInstanceViews is read-only and is used only for post-reconciliation projection.

## Authoritative state

InstanceBindingStore and its journal remain the sole local authority for binding identity, generation, lease, predecessor, checkpoint and causality. This slice introduces no mission database and no parallel source of truth.

## NEXT_VALID_STEP

- PREPARED/PERSISTED -> ATTACH_WORK_RECEIPT
- BOUND -> ACKNOWLEDGE_BOOTSTRAP
- ACTIVE -> CHECKPOINT
- CHECKPOINTED -> REPLACE
- REPLACED -> RECOVER
- CLOSED/REVOKED/HOLD -> HOLD

## Required evidence

Receipts carry mission/run/binding lineage, generation, authority, checkpoint and Hazel hashes, idempotency, correlation and causation references. A projection read is evidence only of a read; it does not grant authority or prove assurance.

## Stop conditions

Execution stops on authority or binding drift, invalid lease, missing checkpoint/predecessor, unproven external effect, request to mutate Command, or recovery mismatch. These states are HOLD, never silently repaired.

## Explicit non-claims

This slice does not claim Work spawning, external Hazel delivery beyond the injected continuity adapter, Command mutation, authoritative H-06 resolution, productive merge, IB9 closure, IB10 start or closure, or Command B10 implementation. IB10 remains NOT_STARTED/HOLD and COMMAND_B10 remains FROZEN.
