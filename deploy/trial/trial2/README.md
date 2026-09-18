# Trial 2 — Persistent Infrastructure

Scope is limited by `DEDALA-TRIAL2-PERSISTENT-INFRASTRUCTURE-EXECUTION-CONTRACT-001`.

This package provides an Option A deployment shape: one long-running trial runtime plus PostgreSQL with a named durable volume. `schema.sql` defines the Trial 2 persistent tables. The runtime entrypoint is `app.single_surface_trial.trial2_asgi:app`.

Required recovery state is persisted in relational tables: mission state, instance bindings, fencing epochs, handoff envelopes, acceptance receipts, checkpoints, autonomy counters, effect idempotency receipts, state namespace hashes, and observability events.

Builder verification may use a file-backed SQLite database to exercise restart semantics without claiming the PostgreSQL substrate was executed. Trial 2 substrate execution must use a persistent relational database and is a separate execution step.

Boundaries:

- production is not authorized;
- merge is not authorized;
- Replit is not an OCS execution substrate;
- self-assurance is forbidden;
- no authority expansion is implied;
- unknown recovery state holds;
- no required checkpoint holds;
- blind retry is forbidden;
- duplicate effects reconcile through mission-scoped idempotency keys.
