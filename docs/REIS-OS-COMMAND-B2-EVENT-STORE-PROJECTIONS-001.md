# REIS-OS-COMMAND-B2-EVENT-STORE-PROJECTIONS-001

STATUS = IMPLEMENTED_ON_BRANCH
PROGRAM = REIS-OS-COMMAND-APPLICATION-001
PREDECESSOR = REIS-OS-COMMAND-B1-READ-CONTRACTS-001
BASE_SHA = ef926b04492e6f278495bd2b109f9162bef54659

## Boundary

Command = contextual projection + intent surface.
Kernel authority and policy are not modified.
Hazel continuity/recovery is not modified.
B3 API is not implemented by this block.

## Event contract

Typed event fields preserve event/schema identity, source and source version,
institution/OCS/project/run correlation, causation/correlation, monotonic sequence,
idempotency key, freshness, evidence references and payload.

Fail closed rules:
- invalid schema -> reject;
- sequence gap -> explicit hold error;
- duplicate idempotent replay -> zero material duplication;
- unknown source -> reject;
- verified/assured claim without evidence -> reject;
- cross-OCS target mismatch -> reject.

## Durable event store

CommandEventStore uses SQLite as the Command-local event persistence boundary.
Rows are append-only through the public API and read in insertion position order.
Sequence uniqueness is scoped to source + institution + OCS + run.
Idempotency keys and event IDs are unique.

## Projections

Minimum read-model surfaces implemented:
- institution;
- OCS;
- operations;
- gates;
- events;
- evidence / receipts;
- system health;
- maps when source events explicitly provide map material.

No-data system health remains UNKNOWN. A non-UNKNOWN health claim without evidence
is projected back to UNKNOWN rather than promoted.

## Deterministic replay

Rebuilding projections from the same ordered stored events produces the same
canonical projection structure.

Required chain is covered by tests:
SOURCE_EVENT -> INGEST -> STORE -> PROJECT -> READ_MODEL -> QUERY -> EVIDENCE_REF.
