# REIS OS Institutional Software Factory V1 — Meta-Architecture

ARCHITECTURE_ID = `NOESIS-META-ARCH-REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001`

OWNER = `NÓESIS`
STATUS = `FORMAL_BASELINE_FOR_RETROACTIVE_CONFORMANCE`

## Mission

Provide one autonomous institutional software-delivery runtime that accepts a build candidate, performs bounded qualification from DEV through STAGING, generates release/evidence artifacts, and stops at the Founder final gate. Production promotion and GitHub merge are never autonomous in V1.

## Authority

- GitHub is source of truth.
- Render Free may be used as a zero-cost qualification runner.
- No paid infrastructure may be created or upgraded without Founder authorization.
- The runtime may qualify a candidate and prepare a FounderGateBundle.
- The runtime may not merge a PR.
- The runtime may not expose a public endpoint that can promote to PRODUCTION.
- Founder approval is required for any production promotion path outside the public runtime API.

## Planes

### 1. Mission / Orchestration Plane
`BuildCandidate -> deterministic gates -> STAGING qualification -> FounderGateBundle`

Required gates: QA, configuration/secrets, migration/rollback, performance/SLO, security baseline, artifact immutability, release manifest.

### 2. Environment Plane
`DEV -> STAGING -> PRODUCTION`

DEV and STAGING can be reached autonomously when prior gates pass. PRODUCTION requires explicit Founder authorization. Direct DEV->PRODUCTION is forbidden.

### 3. Release / Artifact Plane
Every release candidate must bind software_id, version, source_sha, immutable artifact hashes, changelog, rollback_ref and release manifest hash. Artifact overwrite with different bytes under the same identity must fail closed.

### 4. Security Plane
V1 must include a deterministic baseline scanner, secret/config policy and SBOM-like file hashes. V1 must not claim equivalence to full enterprise SAST/SCA/container scanning unless external scanner evidence is attached.

### 5. Evidence / Provenance Plane
Qualification evidence must be bound to a runner reference and cryptographic evidence hashes. Unbound test/performance claims are not sufficient for Founder-gate readiness.

Required provenance fields:
- `runner_ref`
- `qa_evidence_hash`
- `performance_evidence_hash`

Hashes must be SHA-256 hex digests.

### 6. Persistence Plane
V1 may run with process-memory state for bounded qualification, but it must declare that durability class explicitly. Volatile state is acceptable for qualification, not for a claim of production-hardened control-plane durability.

### 7. Observability / Incident Plane
Gate failures create incidents. The runtime emits append-only logical observations sufficient to reconstruct qualification progression within the process lifetime. Production-grade durable telemetry is a later hardening stage.

## Classification

`BOUNDED_V1_READY` means: architecture gates satisfied, exact candidate evidence bound, STAGING qualified, Founder final gate pending.

`PRODUCTION_HARDENED` additionally requires durable state plus external security-tool evidence and durable provenance/telemetry. V1 does not claim this status.

## Fail-closed conditions

The candidate is HOLD when any required gate fails, provenance is absent/invalid, security baseline fails, migration rollback is absent, performance policy is breached, test failures exist, secret material is embedded, or environment ordering is violated.

## Required output

FounderGateBundle must explicitly expose:
- gate status;
- source/release identity;
- QA/security/migration/performance results;
- provenance binding;
- durability class;
- production_hardened flag;
- carried reservations.

## Institutional sequence

`NÓESIS meta-architecture -> DÉDALA architecture assurance -> SÝNESIS independent architecture assurance -> implementation conformance/repair -> ÁGORA qualification -> DÉDALA implementation assurance -> SÝNESIS institutional assurance -> Founder final gate`.
