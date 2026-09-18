# REIS OS Institutional Software Factory V1

ARCHITECTURE_ID = `REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001`

Purpose: provide one autonomous pre-production software delivery lane that executes deterministic institutional gates end-to-end and stops at the final Founder gate.

## Canonical lane

MISSION -> DEV -> QA -> MIGRATION GATE -> PERFORMANCE/SLO GATE -> SECURITY/SBOM -> IMMUTABLE ARTIFACT REGISTRY -> RELEASE MANIFEST -> STAGING -> OBSERVABILITY -> FOUNDER FINAL GATE -> PRODUCTION

Production promotion and GitHub merge are explicitly outside autonomous authority in V1.

## Components

- Release Manager: versioned manifest, changelog, source SHA, artifact hashes, rollback reference.
- Environment Manager: DEV/STAGING/PRODUCTION transition control; production requires explicit Founder approval.
- Security Pipeline: secret-pattern scan, fail-closed policy, SBOM-style file hashes.
- Artifact Registry: immutable software/version/path records with SHA-256.
- Observability: append-style operational events and counters.
- Incident & Recovery: incident lifecycle and rollback references.
- Config Manager: secret-like configuration must be external references (`ref://...`).
- Feature Flags: explicit named toggles, default off.
- Migration Gate: requires forward and rollback plans; destructive changes require explicit acknowledgement.
- Performance Gate: bounded p95 latency and error-rate policy.
- SLO Policy: availability, latency target, and error budget.
- Autonomous Orchestrator: coordinates all pre-gate stages and emits a Founder Gate Bundle.

## Authority

`AUTONOMOUS_PRE_GATE = TRUE`

`PRODUCTION_WITHOUT_FOUNDER = FALSE`

`GITHUB_MERGE_WITHOUT_FOUNDER = FALSE`

`PAID_INFRA_AUTHORIZATION = NONE`

## Founder Gate Bundle

A candidate reaches the final gate only when tests, migration policy, performance policy, security/SBOM, immutable artifact registration, release manifest creation, and staging qualification all pass. The bundle records source SHA, release ID, release manifest hash, SLO policy, and explicit reservations.

## Failure semantics

Any material gate failure returns HOLD, opens an incident where applicable, and does not advance to staging/production. Security and secret-policy violations fail closed.

## V1 runtime target

GitHub is source of truth. Render Free is the external qualification runtime. No Replit dependency is required for this software.
