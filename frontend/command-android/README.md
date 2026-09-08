# REIS OS Command Android — Longitudinal Product Slice

This module is an **executable Android application slice** for the REIS OS Command cockpit.

## What this slice proves structurally

- Android application module with package `com.reisos.command`.
- Launcher Activity and cold-start entrypoint structure.
- Deterministic navigation across S0–S9.
- Local back navigation and recreation-state restoration.
- Primary navigation across S0/S1/S3/S7/S9 plus access to all ten surfaces.
- Explicit CURRENT / PARTIAL / STALE / UNKNOWN / HOLD / DENY / NOT_PROVEN semantics.
- Synthetic fixture boundaries remain visible in the UI.
- Institutional product catalog with all ten OCS names, synthetic operations, evidence records, and system projections.
- EXECUTED never becomes VERIFIED without matching readback.
- UNKNOWN progress never becomes a fabricated percentage.
- Unknown graph relations produce HOLD rather than canonical causal acceptance.
- OCS instance state with missing generation remains PARTIAL.
- Offline manifest boundary: no INTERNET permission.
- Evidence rules require lint, unit tests, longitudinal invariant suites, APK assembly, package/launcher inspection, and a receipt bound to the exact Git SHA.

## Canonical material execution

The canonical execution envelope is:

`ANDROID-MATERIAL-EXECUTION-ENVELOPE.md`

The executor is capability-defined and must provide a real shell, JDK 17, Android SDK/build-tools, Gradle, AAPT, repository access, and binary artifact generation.

Google AI Studio / Gemini Playground was empirically tested and returned `BLOCKED (EXECUTION_ENVIRONMENT_UNAVAILABLE)` for material execution. Its previous product-name binding is deprecated; textual analysis does not replace build evidence.

## Longitudinal surfaces

- S0 — institutional situation
- S1 — operations
- S2 — operation detail / receipt-readback semantics
- S3 — ten-OCS directory
- S4 — OCS detail / incomplete instance semantics
- S5 — causal map / unknown relation HOLD
- S6 — evidence validation
- S7 — evolution projection
- S8 — system availability/freshness
- S9 — conversation/context boundary

## What this slice does not prove

- Live backend connectivity.
- Postgres persistence.
- Real Atlas/L5 hydration.
- AI runtime integration.
- Kernel mutation or authority creation.
- Production readiness.
- Successful material Android build until the canonical envelope completes on an eligible executor.
- Real-device accessibility, TalkBack traversal, focus order on device, or device contrast validation.

## Institutional boundary

`COMMAND_PROJECTION != SOURCE_OF_TRUTH`

`UI_DOES_NOT_CREATE_AUTHORITY`

`EXECUTED != VERIFIED`

`VERIFIED != ASSURED`

`UNKNOWN != ZERO`

`STALE != CURRENT`

`HANDOFF_DOES_NOT_TRANSFER_AUTHORITY`

`CAPABILITY != AUTHORITY`

The product slice is intentionally synthetic so product behavior can be exercised longitudinally without opening authority, persistence, or runtime boundaries prematurely.
