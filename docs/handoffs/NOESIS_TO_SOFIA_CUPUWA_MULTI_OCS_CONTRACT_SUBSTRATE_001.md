# NÓESIS → SOFIA — CUPUWA Multi-OCS Contract Substrate 001

HANDOFF_ID: NOESIS-TO-SOFIA-CUPUWA-MULTI-OCS-CONTRACT-SUBSTRATE-001
SOURCE_OCS: NÓESIS
TARGET_OCS: SOFIA
PRODUCT: CUPUWA
PROGRAM: REIS OS
MISSION_CLASS: MATERIAL_IMPLEMENTATION
TARGET_SLICE: SLICE-001
BOUND_BRANCH: cupuwa/mvp-build
BOUND_HEAD_AT_ISSUE: 5cb0e15e49944624d9e34fa65deb9b29575443f9
UPSTREAM_PLAN: docs/CUPUWA_MULTI_OCS_MATERIALIZATION_PLAN_001.md

MISSION:
Materialize the authority-neutral contract substrate required by the CUPUWA multi-OCS deployment architecture.

REQUIRED_IMPLEMENTATION:
- MissionContract
- SpecialistHandoff
- SpecialistReceipt
- ReconciliationResult
- ImplementationContract
- deterministic validators
- reconciliation states CONSISTENT, CONFLICT, INSUFFICIENT_EVIDENCE, UNKNOWN, HOLD

REQUIRED_INVARIANTS:
- authority_transfer=false
- memory_import=false
- handoff!=material_effect
- no capability adapter introduced
- no tool permission introduced
- no authority expansion
- no implicit SOFIA fallback encoded in routing
- bound_head preserved across handoff
- invalid/missing authority_ref fails closed

REQUIRED_TESTS:
- required fields fail closed
- mission identity cannot silently change across handoff
- bound head cannot silently change across handoff
- authority transfer rejected
- memory import rejected
- material-effect claim rejected at contract layer
- invalid reconciliation state rejected
- CONFLICT cannot produce executable implementation contract
- UNKNOWN cannot produce executable implementation contract
- INSUFFICIENT_EVIDENCE cannot produce executable implementation contract

EVIDENCE_REQUIRED:
- exact resulting HEAD
- changed files
- test names and PASS/FAIL/SKIP counts
- applicable Ruff/Mypy results

PROHIBITIONS:
- no product UI implementation in this slice
- no P0 behavior change
- no adapter/tool binding
- no direct material effect route
- no authority/trust-root expansion
- no Google Play publication
- no automatic PASS
- no fabricated execution evidence

RETURN_TARGET: ÁGORA after material implementation for independent qualification.
