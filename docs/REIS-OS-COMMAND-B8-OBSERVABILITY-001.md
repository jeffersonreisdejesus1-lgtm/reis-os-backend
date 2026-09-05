# REIS-OS-COMMAND-B8-OBSERVABILITY-001

Status: implemented on branch
Base SHA: b396a5216a89f1ee534f0c63a52e4192b422ac99

B8 materializes a correlated Command observability snapshot over durable Command events.

Minimum surfaces represented when evidence exists: run, project, OCS, request, decision, event, receipt, error, latency, health, freshness, correlation and causation.

Semantics are deliberately non-inflationary:
- no events => `status=no_data`, `event_count=null`, `health=unknown`, `freshness=unknown`;
- missing latency => null values, never zero;
- no observed error event => `observed_no_error_event`, not `healthy`;
- any observed error => `degraded`;
- any stale event => aggregate freshness `stale`;
- evidence refs, correlation and causation are preserved from source events.

Query surface: `GET /v1/command/observability`.

No assurance is inferred from observability. B9 is not implemented in this branch.
