# REIS OS Command — non-runtime Android frontend skeleton

Status: `NON_RUNTIME_PREPARATION_ONLY`

This directory materializes the Íris frontend skeleton for REIS OS Command against `COMMAND-AGORA-PRELIMINARY-BACKEND-CONTRACTS-001` and `COMMAND-IRIS-FRONTEND-IMPLEMENTATION-CONTRACT-001`.

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
- `tests` — deterministic contract checks.

No file under this skeleton may claim runtime availability or real institutional data.