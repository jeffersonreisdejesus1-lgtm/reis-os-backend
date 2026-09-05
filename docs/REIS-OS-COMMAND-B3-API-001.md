# REIS-OS-COMMAND-B3-API-001

Status: implemented on branch
Predecessor: REIS-OS-COMMAND-B2-EVENT-STORE-PROJECTIONS-001
Base SHA: 97f45542104f34407316270902d699635797fce5

## Boundary

Command B3 is a read-only API surface over B1 declared OCS profiles and B2 material read models.
It does not execute Kernel intents, write Hazel, perform external effects, promote production,
or claim realtime behavior.

## Routes

- GET /v1/command/institution
- GET /v1/command/ocs
- GET /v1/command/ocs/{ocs_slug}
- GET /v1/command/operations
- GET /v1/command/gates
- GET /v1/command/events
- GET /v1/command/evidence
- GET /v1/command/system-health
- GET /v1/command/maps

All routes inherit the B1 authenticated institutional organization + active owner/admin membership boundary.

Operational routes rebuild B2 projections from the configured Command event store. Material projection entries preserve source, source_version, freshness, evidence_refs, occurred_at, causation_id and correlation_id from their source events.

Empty material collections fail closed with command_projection_not_materialized. System health is the explicit exception: no-data is returned as status=unknown and freshness=unknown, never healthy.

## Proof target

B2_READ_MODEL -> COMMAND_API -> AUTHENTICATED_QUERY -> RESPONSE_WITH_SOURCE_VERSION_FRESHNESS_EVIDENCE

## Non-claims

REQUESTED != EXECUTED
NO_DATA != HEALTHY
UNKNOWN != ZERO
No realtime claim is made.
