# Retroactive Architecture Conformance — PR #98

OBJECT = `REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001`
BASELINE = `NOESIS-META-ARCH-REIS-OS-INSTITUTIONAL-SOFTWARE-FACTORY-V1-001`

## Initial implementation candidate findings

C01 — Authority boundary: PASS after removal of the public production-promotion endpoint.

C02 — Environment ordering: PASS. DEV precedes STAGING; PRODUCTION requires Founder approval.

C03 — Release/artifact immutability: PASS.

C04 — Security baseline: PASS_WITH_SCOPE_LIMIT. Deterministic secret scanning and SBOM-like hashing exist, but they are not full external SAST/SCA/container assurance.

C05 — Persistence: PASS_WITH_RESERVATION. Runtime state is process-memory and therefore bounded-qualification only.

C06 — Evidence provenance: REPAIR_REQUIRED. Test/performance values were accepted from the candidate contract without cryptographic binding to runner evidence.

C07 — Product claim boundary: REPAIR_REQUIRED. FounderGateBundle did not explicitly distinguish bounded V1 readiness from production-hardening readiness.

## Required repairs

R01 — Add runner/evidence binding fields and fail closed when hashes are absent or malformed.

R02 — Expose `durability_class`, `security_assurance_class`, and `production_hardened` on FounderGateBundle.

R03 — Carry explicit reservations for volatile state and baseline-only security when bounded qualification passes.

R04 — Add tests proving missing/invalid provenance produces HOLD and proving V1 never claims `production_hardened=true`.

## Disposition before repair

`TARGETED_REPAIR_REQUIRED`

The implementation candidate remains usable as a repair base; no rebuild-from-zero is required.
