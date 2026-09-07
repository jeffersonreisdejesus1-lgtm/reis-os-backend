# REIS OS Command B10 — CUPUWA-inspired OCS/AI Module

DOCUMENT_ID: `COMMAND-B10-CUPUWA-OCS-AI-ARCHITECTURE-001`
STATUS: `IMPLEMENTATION_CANDIDATE`
MODE: `ADDITIVE_PRODUCTIZATION`
BASELINE: `IB10_REVISED_CLOSED_WITH_RESERVATIONS`

## 0. Purpose

Materialize Command B10 as a product surface over existing REIS OS state while adding a CUPUWA-inspired module with an OURO/PRATA split and a shared OCS-aware inference fabric.

This tranche does not create a new institutional source of truth and does not make model inference authoritative.

## 1. Product principles

`SIMPLE_SURFACE + DEEP_COMPETENCE + ONE_HAND_FRIENDLY + MODEST_DEVICE_COMPATIBILITY + HIGH_RELIABILITY`

`COMMAND != SOURCE_OF_TRUTH`
`COMMAND != PROMOTION_DECIDER`
`MODEL != OCS`
`INFERENCE != AUTHORITY`
`REQUESTED != EXECUTED`
`EXECUTED != VERIFIED`
`VERIFIED != ASSURED`
`UI_DOES_NOT_CREATE_AUTHORITY`

## 2. Product architecture

```text
COMMAND
├── CORE OPERACIONAL
│   ├── institution
│   ├── 10 OCS profiles
│   ├── missions / operations
│   ├── gates / evidence
│   ├── instances / lineage
│   ├── recovery center
│   ├── capability / federated-seat health
│   └── realtime / observability
│
└── CUPUWA-INSPIRED MODULE
    ├── OURO
    │   ├── deterministic facts
    │   ├── canonical/bounded projections
    │   ├── evidence
    │   ├── history / lineage
    │   ├── state health
    │   └── remains usable if PRATA is unavailable
    │
    └── PRATA
        ├── OCS-aware inference
        ├── general AI assistance
        ├── tool-assisted retrieval
        ├── recommendations
        ├── cross-OCS routing
        ├── automation preparation
        └── optional provider/model invocation
```

`PRATA_FAILURE != OURO_FAILURE`

## 3. Shared OCS inference fabric

One shared mechanism is reused by every module and every OCS.

```text
OCS_GENERIC_INFERENCE_FABRIC
+ OCS_ID / optional
+ PROFILE
+ MISSION CONTEXT
+ AUTHORITY ENVELOPE
+ NAMESPACES
+ REQUEST SCOPE
+ TOOL / HOST CAPABILITIES
+ INFERENCE POLICY
→ RESPONSE PLAN
```

The engine is not an OCS. A bound execution under an OCS profile is an OCS-level inference instance.

### Response modes

- `GENERAL_AI` — general assistance with no institutional specialist claim.
- `OCS_SPECIALIST` — inference under one explicit OCS profile/binding.
- `ROUTED_OCS` — bounded routing to a better OCS.
- `TOOL_ASSISTED` — requires an available source/tool capability.
- `AUTHORITY_GATED` — may prepare/recommend an action but cannot execute until policy/authority/receipt gates pass.
- `HOLD` — unsafe, ambiguous, unavailable or structurally invalid request.

### Out-of-scope behavior

Out-of-specialty is not an error. General harmless tasks may fall back to `GENERAL_AI`. Material actions do not fall back around authority.

Anti-loop invariants:

`MAX_ROUTING_HOPS = 2`
`SAME_REQUEST_SAME_OCS_REENTRY = PROHIBITED`
`NO_VALID_SPECIALIST_ROUTE → GENERAL_AI | HOLD`

## 4. OURO behavior

OURO may expose facts and deterministic projections and may ask PRATA for explanations, summaries or anomaly suggestions. OURO does not depend on inference for truth.

Allowed inference over OURO:
- explain;
- summarize;
- compare;
- detect anomaly;
- suggest next action.

Prohibited direct path:

`INFERENCE → CANONICAL_STATE_WRITE`

## 5. PRATA behavior

PRATA is the first-class intelligence layer:
- general assistance;
- OCS specialist reasoning;
- cross-OCS routing;
- tool/source retrieval;
- provider/model invocation when capability is materially available;
- planning and automation preparation.

PRATA may propose but cannot self-grant authority or promotion.

## 6. Metrics architecture

Metrics are diagnostic and cannot create PASS, authority or promotion.

### M1 — Core independence
- `ouro_available_when_prata_unavailable_rate` target = 100%
- `prata_failure_causing_ouro_failure` target = 0

### M2 — Routing correctness
- `request_route_resolved_rate`
- `general_fallback_rate`
- `specialist_route_rate`
- `invalid_ocs_hold_rate`
- `routing_loop_count` target = 0
- `routing_hops_p95` target <= 2

### M3 — Authority safety
- `direct_inference_state_write_count` target = 0
- `authority_bypass_count` target = 0
- `self_promotion_count` target = 0
- `material_action_without_receipt_count` target = 0

### M4 — Epistemic clarity
- `responses_with_mode_label_rate` target = 100%
- `responses_with_provenance_boundary_rate` target = 100%
- `unknown_as_healthy_count` target = 0
- `inference_as_fact_misclassification_count` target = 0

### M5 — Capability/tool behavior
- `tool_request_without_capability_attempt_count` target = 0
- `source_access_model_invocation_conflation_count` target = 0
- `live_model_invocation_without_adapter_receipt_count` target = 0

### M6 — Product quality
- cockpit/module endpoint latency p50/p95;
- accessibility findings by severity;
- mobile one-hand critical-flow completion;
- stale projection exposure rate;
- recovery/readback success rate.

## 7. Pipeline

```text
B10-AR0 RECOVER + FREEZE BASELINE
→ B10-AR1 PRODUCT / INFORMATION ARCHITECTURE
→ B10-AR2 OURO / PRATA MODULE CONTRACT
→ B10-AR3 OCS INFERENCE FABRIC
→ B10-AR4 TOOL + HOST / PROVIDER CAPABILITY BOUNDARY
→ B10-AR5 BOUNDED CONTROL SURFACE
→ B10-AR6 METRICS + OBSERVABILITY
→ B10-AR7 E2E / NEGATIVE / IDEMPOTENCY / RECOVERY
→ B10-AR8 UX + ACCESSIBILITY REVIEW
→ B10-AR9 EXACT-HEAD FREEZE
→ B10-AR10 ADVERSARIAL / FEDERATED ASSURANCE
→ FOUNDER PROMOTION DECISION
```

## 8. Action plan

1. Preserve existing Command projections and IB6 instance/recovery views.
2. Add aggregate cockpit without new persistence.
3. Add CUPUWA-inspired module descriptor and OURO/PRATA contract.
4. Add shared OCS inference planning policy.
5. Add general-assistance fallback and anti-loop routing.
6. Add tool/source capability requirement for retrieval tasks.
7. Keep material actions authority-gated.
8. Add metrics definitions and read-only health projection.
9. Add negative tests for authority bypass, invalid OCS, loops and PRATA isolation.
10. Run Command, governance, Chat Runtime, Execution Plane, Hazel and StateCore regressions.
11. Freeze exact HEAD.
12. Run independent adversarial assurance.

## 9. Gate architecture

Four levels are preserved:

- `L0 MICRO_GATE`
- `L1 OPERATION_GATE`
- `L2 PHASE_GATE`
- `L3 PROGRAM_PROMOTION_GATE`

`ONE_MICRO_GATE = ONE_MATERIAL_CLAIM + ONE_BOUNDED_TRANSITION + ONE_EVIDENCE_PACKAGE`

### G-B10-0 — Baseline integrity
PASS when base SHA/readback is exact and no hidden parallel SoR is introduced.

### G-B10-1 — Product projection
PASS when cockpit composes existing sources only and UNKNOWN is not converted to healthy/zero.

### G-B10-2 — OURO/PRATA isolation
PASS when PRATA can be absent/failed without breaking OURO and no inference creates canonical truth.

### G-B10-3 — OCS inference fabric
PASS when GENERAL_AI, OCS_SPECIALIST, TOOL_ASSISTED, AUTHORITY_GATED and HOLD are deterministic at the policy boundary; invalid OCS and routing loops fail closed.

### G-B10-4 — Capability/tool boundary
PASS when source access and model invocation are independent and unavailable tool/provider capability cannot be fabricated.

### G-B10-5 — Material-action authority
PASS when action preparation cannot bypass authority, promotion or receipt/readback requirements.

### G-B10-6 — E2E / negative / recovery
PASS when regressions, tenant isolation, idempotency, fencing and recovery remain green.

### G-B10-7 — UX/accessibility
PASS when critical mobile flows remain comprehensible, one-hand friendly and accessible.

### G-B10-8 — Exact-head independent assurance
PASS/PASS_WITH_RESERVATIONS only on exact frozen HEAD with material blockers = 0.

### G-B10-9 — Founder promotion
Founder-reserved explicit act only. No software metric can auto-pass this gate.

Every gate declares `on_pass`, `on_fail`, `on_hold`, `on_indeterminate` and emits a receipt before state transition.

## 10. Delivery agenda

### Architecture agenda
1. current architectural state;
2. closed/open components;
3. active gate/micro-gate;
4. material conflicts/evidence;
5. readiness status;
6. next architecture/action.

### Operational agenda
1. repository / exact HEAD;
2. implementation delta;
3. tests / CI;
4. blockers / reservations;
5. assurance state;
6. next action.

### Founder agenda
1. where are we?;
2. what was proven?;
3. what remains a reservation?;
4. who owns the next gate?;
5. is Founder action required?;
6. what happens next?

## 11. Source-of-truth boundary

- institutional mission/identity/authority: existing REIS OS canonical stores/contracts;
- Execution Plane: bounded execution ledger;
- governance candidate store: governance/evidence overlay;
- Command: projection + bounded control surface;
- OCS inference fabric: cognitive/planning capability, not canonical persistence.

No direct UI, model or inference output becomes institutional truth without the existing execution/authority/evidence path.
