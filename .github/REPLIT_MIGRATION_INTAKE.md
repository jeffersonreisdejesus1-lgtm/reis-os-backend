# Replit → GitHub Migration Intake

MIGRATION_PROTOCOL_ID = REIS-OS-REPLIT-TO-GITHUB-INTAKE-001

A software leaves Replit only through this intake.

## Required intake record

- SOFTWARE_NAME
- CURRENT_REPLIT_PROJECT
- TARGET_REPOSITORY
- SOFTWARE_CLASS = CORE | PRODUCT | INFRASTRUCTURE | TOOL
- OWNER_OCS
- RUNTIME_TARGET = RENDER | VERCEL | CODEMAGIC | NONE | OTHER
- LANGUAGE / FRAMEWORK
- ENTRYPOINT
- DEPENDENCIES
- DATABASE / PERSISTENCE
- ENVIRONMENT_VARIABLE_NAMES
- SECRET_VALUES_EXPORTED = FORBIDDEN
- BUILD_COMMAND
- START_COMMAND
- TEST_COMMAND
- CURRENT_PUBLIC_URL
- REQUIRED_DATA_MIGRATION
- REQUIRED_ASSETS
- REPLIT_ONLY_DEPENDENCIES
- CUTOVER_PLAN
- ROLLBACK_PLAN

## Gates

G0 INVENTORY_COMPLETE
G1 TARGET_REPOSITORY_RESOLVED
G2 SOURCE_EXPORT_COMPLETE
G3 SECRET_SANITIZATION_PASS
G4 DEPENDENCIES_RESOLVED
G5 BUILD_PASS
G6 TEST_PASS_OR_EXPLICIT_RESERVATION
G7 TARGET_RUNTIME_DEPLOYED
G8 FUNCTIONAL_EQUIVALENCE_VERIFIED
G9 CUTOVER_AUTHORIZED
G10 REPLIT_DECOMMISSION_CANDIDATE

## Rules

- No secret value is committed to GitHub.
- `.env.example` may contain names/placeholders only.
- A Replit project is not canceled before the replacement runtime is verified.
- Migration is not considered complete merely because source code was copied.
- `SOURCE_COPIED != BUILD_VERIFIED != RUNTIME_VERIFIED != CUTOVER_COMPLETE`.
- Production activation requires its own authorization.
- If the target is Android, build responsibility may route to Codemagic.
- If the target is backend/API/worker, Render is the default current hosting target unless architecture says otherwise.
- If the target is web frontend, Vercel may be used when appropriate.

## Default migration order

1. Inventory software in Replit.
2. Classify each software and resolve its target repository.
3. Export source without secrets.
4. Rebuild deterministically outside Replit.
5. Run tests.
6. Deploy to target runtime.
7. Verify functional equivalence.
8. Authorize cutover.
9. Only then consider Replit project decommissioning.
