# REIS OS Command B10 — CUPUWA-inspired OCS/AI Module

DOCUMENT_ID: `COMMAND-B10-CUPUWA-OCS-AI-ARCHITECTURE-001`
STATUS: `IMPLEMENTATION_CANDIDATE`
MODE: `ADDITIVE_PRODUCTIZATION`
BASELINE: `IB10_REVISED_CLOSED_WITH_RESERVATIONS`

## 0. Purpose

Materialize Command B10 as a product/control surface over existing REIS OS state while adding a CUPUWA-inspired module with an OURO/PRATA split and a shared OCS-aware inference fabric.

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

Every metric record MUST carry:

```text
SOURCE_REF
MEASUREMENT_METHOD
MEASUREMENT_VERSION
OBSERVED_AT
WINDOW
COMPLETENESS
UNKNOWN_SEMANTICS
```

Anti-Goodhart rules:

```text
NO_SINGLE_METRIC_CAN_PROMOTE
NO_SINGLE_METRIC_CAN_CLOSE_QUALITY_GATE
NO_METRIC_CAN_OVERRIDE_EVIDENCE
NO_METRIC_CAN_SUPPRESS_REQUIRED_ESCALATION
```

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
→ B10-AR8 UX + ACCESSIBILITY ASSESSMENT
→ B10-AR9 EXACT-HEAD FREEZE
→ B10-AR10 ADVERSARIAL / FEDERATED ASSURANCE
→ PROMOTION READINESS
→ FOUNDER APPROVAL
```

## 8. Action plan

1. Preserve existing Command projections and IB6 instance/recovery views.
2. Add aggregate cockpit without new persistence.
3. Add CUPUWA-inspired module descriptor and OURO/PRATA contract.
4. Add shared OCS inference planning policy.
5. Add general-assistance fallback and anti-loop routing.
6. Add tool/source capability requirement for retrieval tasks.
7. Keep material actions authority-gated.
8. Add metrics definitions with anti-Goodhart metadata.
9. Add negative tests for authority bypass, invalid OCS, loops and PRATA isolation.
10. Run Command, governance, Chat Runtime, Execution Plane, Hazel and StateCore regressions.
11. Run UX/accessibility assessment when a frontend surface exists.
12. Freeze exact HEAD.
13. Run independent adversarial/federated assurance.
14. Founder approval remains an explicit reserved act.

## 9. Gate architecture

The current REIS OS gate grammar remains canonical. B10 does not create a parallel macro-gate system.

```text
G0 — EXECUTION GATE
G1 — TECHNICAL QUALITY GATE
G2 — INDEPENDENT ASSURANCE GATE (CONDITIONAL / POLICY-BOUND)
G3 — PROMOTION READINESS GATE
G4 — FOUNDER APPROVAL GATE
```

Flow:

```text
MATERIAL BUILD
→ DOMAIN ASSESSMENTS AS_REQUIRED
→ EVIDENCE AGGREGATION
→ TECHNICAL QA / CONFORMANCE
→ INDEPENDENT ASSURANCE IF_REQUIRED
→ PROMOTION READINESS
→ FOUNDER APPROVAL
```

B10-specific claims are assessments/micro-gates inside this grammar, not new institutional macro-gates:

- `A-B10-BASELINE` — exact base/readback and no parallel SoR.
- `A-B10-PROJECTION` — cockpit composes existing sources; UNKNOWN is not healthy/zero.
- `A-B10-OURO-PRATA` — PRATA can fail without breaking OURO; inference creates no canonical truth.
- `A-B10-INFERENCE` — response modes, invalid OCS and anti-loop behavior are bounded.
- `A-B10-CAPABILITY` — source access and model invocation stay distinct; unavailable capability is not fabricated.
- `A-B10-AUTHORITY` — preparation cannot bypass authority/promotion/receipt/readback.
- `A-B10-E2E` — regressions, isolation, idempotency, fencing and recovery.
- `A-B10-UX` — mobile/interaction/accessibility assessment when a frontend exists.

Each material assessment declares evidence, verifier, verdict and routing. No receipt means no accepted state transition.

## 10. Delivery agenda

### Architecture agenda
1. current architectural state;
2. closed/open components;
3. active gate + assessments;
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
4. who owns the next assessment/gate?;
5. is Founder action required?;
6. what happens next?

## 11. Source-of-truth boundary

- institutional mission/identity/authority: existing REIS OS canonical stores/contracts;
- Execution Plane: bounded execution ledger;
- governance candidate store: governance/evidence overlay;
- Command: projection + bounded control surface;
- OCS inference fabric: cognitive/planning capability, not canonical persistence.

No direct UI, model or inference output becomes institutional truth without the existing execution/authority/evidence path.

## 12. Current productization boundary

The repository currently materializes backend/control contracts and APIs. No distinct Command frontend codebase or previously frozen frontend stack was located in the accessible repositories/artifacts at this point. Therefore:

`BACKEND_CONTROL_CONTRACT = MATERIALIZABLE`
`FRONTEND_PRODUCT_EXPERIENCE = NOT_YET_PROVEN`
`UX_ACCESSIBILITY_GATE = HOLD_UNTIL_FRONTEND_SURFACE_EXISTS`

Creating a new frontend repository/stack is a material architecture decision and is not silently inferred from backend productization.
