# REIS OS Command — non-runtime Android frontend

Status: `NON_RUNTIME_SYNTHETIC_UI_COMPONENTS`

This directory materializes the Íris frontend for REIS OS Command against `COMMAND-AGORA-PRELIMINARY-BACKEND-CONTRACTS-001` and `COMMAND-IRIS-FRONTEND-IMPLEMENTATION-CONTRACT-001`.

It intentionally contains no live transport, Postgres, Atlas, L5, AI runtime, Kernel mutation, or production wiring.

Hard boundaries:

- `UI_DOES_NOT_CREATE_AUTHORITY`
- `UI_TAP != CANONICAL_MUTATION`
- `PROJECTION != SOURCE_OF_TRUTH`
- `SYNTHETIC_FIXTURE != INSTITUTIONAL_STATE`
- `REQUESTED != EXECUTED != VERIFIED != ASSURED`
- `UNKNOWN != ZERO`
- `STALE != CURRENT`
- `NO_DATA != HEALTHY`

Prepared layers:

- `contracts` — typed preliminary projection/envelope models used by the UI boundary;
- `ui_state` — explicit screen-state grammar;
- `adapters` — safe projection-to-UI mappings;
- `navigation` — S0–S9 route contract;
- `fixtures` — synthetic-only scenarios with mandatory fixture metadata;
- `ui/components` — real Android `View` components with text-first state semantics and accessibility descriptions;
- `ui/screens` — Android S0 synthetic rehearsal surface;
- `tests` — deterministic contract checks.

This folder is now a standalone Android library build target through `settings.gradle.kts` and `build.gradle.kts`. The material Android layer currently proves only source-level component structure. It does **not** prove device behavior, TalkBack traversal, contrast, dynamic text, one-hand use, or production readiness.

Dédala reservation remains frozen:

- `COMMAND_GRAPH_RELATION = PRELIMINARY_PROJECTION_ENUM`
- `COMMAND_GRAPH_RELATION != ATLAS_EDGE_VOCAB`
- `REAL_UI_ACCESSIBILITY = NOT_PROVEN`

No file under this module may claim runtime availability or real institutional data.