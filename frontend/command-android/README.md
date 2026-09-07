# REIS OS Command Android — Longitudinal Product Slice

This module is an **executable Android application slice** for the REIS OS Command cockpit.

## What this slice proves

- Android application module with package `com.reisos.command`.
- Launcher Activity and cold-start shell.
- Deterministic navigation across S0–S9.
- Explicit CURRENT / PARTIAL / STALE / UNKNOWN / HOLD / DENY / NOT_PROVEN semantics.
- Synthetic fixture boundaries remain visible in the UI.
- EXECUTED never becomes VERIFIED without matching readback.
- UNKNOWN progress never becomes a fabricated percentage.
- Unknown graph relations produce HOLD rather than canonical causal acceptance.
- OCS instance state with missing generation remains PARTIAL.
- Back navigation is local to the synthetic application shell.
- CI runs lint, unit tests, longitudinal invariant suites, and produces a debug APK.

## What this slice does not prove

- Live backend connectivity.
- Postgres persistence.
- Real Atlas/L5 hydration.
- AI runtime integration.
- Kernel mutation or authority creation.
- Production readiness.
- Real-device accessibility, TalkBack traversal, focus order on device, or device contrast validation.

## Institutional boundary

`COMMAND_PROJECTION != SOURCE_OF_TRUTH`

`UI_DOES_NOT_CREATE_AUTHORITY`

`EXECUTED != VERIFIED`

`VERIFIED != ASSURED`

`UNKNOWN != ZERO`

`STALE != CURRENT`

The product slice is intentionally synthetic so that product behavior can be exercised longitudinally without opening authority, persistence, or runtime boundaries prematurely.
