# CUPUWA — Multi-OCS Materialization Plan 001

PLAN_ID: CUPUWA-MULTI-OCS-MATERIALIZATION-PLAN-001
UPSTREAM_HANDOFF: DEDALA-TO-NOESIS-CUPUWA-MULTI-OCS-CONTRACT-MATERIALIZATION-001
PRODUCT: CUPUWA
PROGRAM: REIS OS
BOUND_BRANCH: cupuwa/mvp-build
BOUND_HEAD_AT_PLANNING: 887b6b4aadf71e3e7a160a815abd4bdf23d3a53f
DISPOSITION: READY_FOR_FIRST_MATERIAL_SLICE

## 1. Canonical mission contract

Every specialist mission is immutable in identity and must contain:

- mission_id
- product
- increment_id
- bound_object
- bound_head
- requested_outcome
- constraints
- authority_ref
- required_capabilities
- evidence_policy
- completion_policy

A mission without authority_ref, bound_head or evidence policy is HOLD and cannot reach an effect cell.

## 2. Deterministic routing contract

Routing is capability-driven, not roster-wide:

required_capability -> canonical specialty/support scope -> allowed_action_class -> selected OCS

Rules:
- activate only OCS required by the increment;
- no implicit fallback to SOFIA;
- ambiguous or duplicate ownership is CONFLICT and requires reconciliation;
- unsupported capability is HOLD;
- routing does not grant material authority.

Canonical CUPUWA specialist mapping:
AURA=visual direction; EIKÓN=UI/screens/states; TÝPOS=design system/components/tokens; GRAMMÉ=layout/grid/spacing; LÉXIS=UX writing; CHRÔMA=color/contrast; SÊMA=iconography; KINÉSIS=motion; FIGMA=design materialization/prototype; DÉSMOS=Figma components/variants/variables; GÉPHYRA=design-to-code mapping; HÉSTIA=mobile UI implementation; ROTA=navigation; PRÁXIS=interaction/forms/input; MORPHÉ=responsive UI; ARGOS=independent visual QA; DOKIMÉ=independent UX QA; LEÍA=polish/consistency; KRITÉRION=integrated readiness; SOFIA=general software implementation/integration when explicitly required.

## 3. Specialist handoff contract

Required fields:
- mission_id
- source_ocs
- target_ocs
- bound_object
- bound_head
- scope
- inputs
- expected_outputs
- authority_envelope_ref
- required_capabilities
- tool_permissions
- evidence_requirements
- completion_criteria
- failure_state
- predecessor_receipts

Invariants:
authority_transfer=false
memory_import=false
handoff!=material_effect
NO_EVIDENCE->NO_CLAIM

## 4. Parallel specialist cognition

Specialist cognition may run in parallel only when:
- mission_id and bound_head are identical and immutable;
- OCS state and memory remain isolated;
- each specialist produces an independent receipt;
- no branch is authorized for material effect during specialist cognition;
- conflicting outputs enter reconciliation rather than last-writer-wins.

For CUPUWA-P0-ONBOARDING the initial cognition cell is:
ÍRIS + LÉXIS + EIKÓN + TÝPOS + GRAMMÉ + CHRÔMA.

## 5. Reconciliation contract

States:
CONSISTENT
CONFLICT
INSUFFICIENT_EVIDENCE
UNKNOWN
HOLD

Only CONSISTENT may produce a consolidated implementation contract. CONFLICT, INSUFFICIENT_EVIDENCE and UNKNOWN fail closed to HOLD until resolved by evidence or explicit authorized decision. Silent conflict resolution is prohibited.

## 6. Implementation contract

The consolidated implementation object contains:
- mission identity and bound head;
- accepted specialist decisions;
- source receipt for every accepted decision;
- unresolved findings (must be empty for execution);
- exact files/components/routes/interactions in scope;
- effect capabilities required;
- authority envelope reference;
- lease requirements;
- tests and evidence required.

SOFIA is selected only for explicit general software/integration capability. Undefined work cannot be routed to SOFIA by default.

## 7. Material effect boundary

The only valid material path is:

CAPABILITY -> AUTHORITY ENVELOPE -> LEASE -> EFFECTOR -> MATERIAL EFFECT -> RECEIPT

A specialist profile never receives unrestricted tools. capability_adapters/tool_permissions remaining empty in the canonical registry is preserved until a governed effect adapter exists. Direct-effect and lateral-effect routes are prohibited.

## 8. Effect cell

HÉSTIA: mobile UI materialization.
ROTA: navigation/routes/back-stack.
PRÁXIS: forms/input/keyboard/interaction behavior.
MORPHÉ: viewport/density/orientation/responsive adaptation.
SOFIA: general software/integration only when explicitly selected by capability.

Each effect operation requires its own valid authority envelope, bounded lease, effect receipt and idempotency identity.

## 9. Validation topology

Construction -> ARGOS (visual fidelity) + DOKIMÉ (UX/journey behavior) -> LEÍA (polish requirements when applicable) -> KRITÉRION (integrated readiness) -> ÁGORA (technical/reproducibility qualification) -> SÝNESIS only where independent assurance is required.

No validator may self-qualify construction it materially produced. No validation result automatically promotes product state.

## 10. Failure semantics

Missing adapter = HOLD
Missing tool permission = HOLD
Missing authority envelope = HOLD
Expired/invalid lease = DENIED + HOLD
Unavailable OCS = HOLD or authorized reroute only if another canonical capability owner exists
Conflicting specialist outputs = CONFLICT -> HOLD
Incomplete evidence = INSUFFICIENT_EVIDENCE -> HOLD
Partial material execution = reconcile receipts/state before retry
Receipt failure = UNKNOWN -> reconcile before replay
Unknown material state = UNKNOWN -> no re-execution until reconciliation

Replay must not create new authority, new evidence credit or duplicate material effect.

## 11. CUPUWA P0 migration

Existing valid CUPUWA P0 artifacts are inputs, not discarded work. They must be rebound to the current branch/head and classified as ACCEPTED, STALE, CONFLICTING or INSUFFICIENT_EVIDENCE before reuse.

First target increment: CUPUWA-P0-ONBOARDING.

Target path:
ÍRIS + LÉXIS + EIKÓN + TÝPOS + GRAMMÉ + CHRÔMA
-> reconciliation
-> GÉPHYRA
-> HÉSTIA / ROTA / PRÁXIS as required
-> ARGOS + DOKIMÉ
-> KRITÉRION
-> ÁGORA.

## 12. Ordered materialization slices

SLICE-001 — Contract substrate
Responsible OCS: SOFIA
Target: implement pure, authority-neutral data contracts and deterministic validation for MissionContract, SpecialistHandoff, SpecialistReceipt, ReconciliationResult and ImplementationContract.
Repository target: new CUPUWA orchestration/contract module plus isolated tests; canonical profile registry must not be weakened.
Tests: required-field validation; immutable mission/bound-head semantics; authority_transfer=false; memory_import=false; no handoff-as-effect; reconciliation state validation; no implicit SOFIA fallback.
Evidence: source diff, deterministic tests, exact HEAD readback, static checks applicable to changed slice.
Predecessor: this plan.
Authority boundary: NO effect adapters, NO tool permissions, NO material effect.
Rollback/HOLD: any registry weakening, authority expansion or non-deterministic contract behavior -> HOLD.

SLICE-002 — Deterministic capability router
Responsible OCS: SOFIA implementing DÉDALA/NÓESIS contract.
Dependency: SLICE-001 qualified.
Target: capability-to-OCS routing with no roster-wide fan-out and no implicit SOFIA fallback.

SLICE-003 — Reconciliation engine
Responsible OCS: SOFIA.
Dependency: SLICE-002 qualified.
Target: CONSISTENT/CONFLICT/INSUFFICIENT_EVIDENCE/UNKNOWN/HOLD semantics and receipt aggregation.

SLICE-004 — Governed effect bridge
Responsible architecture: DÉDALA; material implementation: SOFIA.
Dependency: SLICE-003 qualified.
Target: capability -> authority envelope -> lease -> effector -> receipt. This is the first slice allowed to introduce effect adapters, and only under separate qualification.

SLICE-005 — Specialist effect bindings
Responsible OCS by capability: HÉSTIA/ROTA/PRÁXIS/MORPHÉ, with SOFIA only for integration support.
Dependency: SLICE-004 qualified.
Target: bounded adapters and permissions per specialist; no unrestricted tool route.

SLICE-006 — CUPUWA P0 onboarding migration
Responsible orchestration: NÓESIS.
Dependency: SLICE-005 qualified.
Target: execute the specialist path against existing P0 artifacts, reconcile, implement and validate.

## 13. First executable implementation handoff

HANDOFF_ID: NOESIS-TO-SOFIA-CUPUWA-MULTI-OCS-CONTRACT-SUBSTRATE-001
SOURCE_OCS: NÓESIS
TARGET_OCS: SOFIA
MISSION_CLASS: MATERIAL_IMPLEMENTATION
TARGET_SLICE: SLICE-001
BOUND_BRANCH: cupuwa/mvp-build
BOUND_HEAD: 887b6b4aadf71e3e7a160a815abd4bdf23d3a53f
MISSION: Materialize the authority-neutral contract substrate required by the CUPUWA multi-OCS deployment architecture.

REQUIRED_IMPLEMENTATION:
- MissionContract
- SpecialistHandoff
- SpecialistReceipt
- ReconciliationResult
- ImplementationContract
- deterministic validators for all contracts
- explicit reconciliation state enum: CONSISTENT, CONFLICT, INSUFFICIENT_EVIDENCE, UNKNOWN, HOLD

REQUIRED_INVARIANTS:
- authority_transfer=false
- memory_import=false
- handoff!=material_effect
- no capability adapter introduced
- no tool permission introduced
- no authority expansion
- no implicit SOFIA fallback encoded in routing
- bound_head preserved by contracts
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
- insufficient evidence cannot produce executable implementation contract

EVIDENCE_REQUIRED:
- exact resulting HEAD
- changed files
- test names and PASS/FAIL/SKIP counts
- applicable Ruff/Mypy results
- no evidence fabrication

PROHIBITIONS:
- no product UI implementation in this slice
- no P0 behavior change
- no adapter/tool binding
- no direct material effect route
- no authority/trust-root expansion
- no Google Play publication
- no automatic PASS

RETURN_TARGET: ÁGORA after material implementation for independent qualification.

## 14. Disposition

DISPOSITION: READY_FOR_FIRST_MATERIAL_SLICE
NEXT_HANDOFF: NOESIS-TO-SOFIA-CUPUWA-MULTI-OCS-CONTRACT-SUBSTRATE-001
