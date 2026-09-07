# REIS OS Command B10 — CUPUWA-inspired OCS/AI Module

DOCUMENT_ID: `COMMAND-B10-CUPUWA-OCS-AI-ARCHITECTURE-001`
STATUS: `IMPLEMENTATION_CANDIDATE`
MODE: `EVOLUTIONARY_PRODUCTIZATION`
BASELINE: `IB10_REVISED_CLOSED_WITH_RESERVATIONS`
LEGACY_UI_BASELINE: `feature/reis-os-command-v0.1-observar/app/command/frontend/index.html`

## 0. Purpose

Materialize Command B10 as a Founder-exclusive product/control surface over existing REIS OS state, evolve the historical Command OBSERVAR frontend instead of discarding it, and add a CUPUWA-inspired management module with OURO/PRATA plus a shared OCS-aware inference fabric.

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

## 2. Metaarquitetura

```text
FOUNDER INTENT
→ COMMAND FOUNDER EXPERIENCE
→ CORE OPERATIONAL OBSERVATORY
   → operations / missions
   → 10 OCS identities
   → gates / evidence / assurance
   → instances / lineage / recovery
   → capability / seat health
→ CUPUWA-INSPIRED MANAGEMENT MODULE
   → OURO: deterministic operational truth/readback
   → PRATA: intelligence / inference / augmentation
→ SHARED OCS INFERENCE FABRIC
   → GENERAL_AI | OCS_SPECIALIST | ROUTED_OCS | TOOL_ASSISTED | AUTHORITY_GATED | HOLD
→ TOOL / HOST / PROVIDER CAPABILITY BOUNDARY
→ AUTHORITY / POLICY GATE
→ KERNEL / HAZEL / EXECUTION PATH WHEN MATERIAL ACTION IS AUTHORIZED
→ RECEIPT + READBACK + EVIDENCE
→ COMMAND PROJECTION
→ FOUNDER DECISION WHEN RESERVED
```

### Metaarquitetural invariants

```text
OLD_COMMAND_OBSERVAR = LEGACY_PRESENTATION_BASELINE
B10 = EVOLUTIONARY_DELTA
NO_REWRITE_BY_FASHION = TRUE
REUSE_LEGACY_FRONTEND_WHERE_COMPATIBLE = TRUE
LEGACY_BRANCH_REMAINS_UNTOUCHED = TRUE

COMMAND = PROJECTION + BOUNDED_CONTROL_SURFACE
COMMAND != INSTITUTIONAL_SOR
COMMAND != PROMOTION_DECIDER

OCS_GENERIC_INFERENCE_FABRIC != OCS
MODEL != OCS
HOST != OCS
INFERENCE != AUTHORITY

OURO_TRUTH_DOES_NOT_DEPEND_ON_PRATA = TRUE
PRATA_FAILURE != OURO_FAILURE
```

The historical OBSERVAR baseline already proved a useful presentation direction: private access, summary-first situation/attention/blockers/decisions/assurance, provenance on demand and read-oriented conversation. B10 keeps that lineage while replacing obsolete API/auth assumptions and extending the surface with current cockpit, ten-OCS identity, recovery, OURO/PRATA and OCS/AI planning.

## 3. Product architecture

```text
COMMAND
├── CORE OPERACIONAL
│   ├── institution
│   ├── 10 OCS profiles
│   ├── missions / operations
│   ├── gates / evidence / assurance
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

## 4. Shared OCS inference fabric

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

Out-of-specialty is not an error. Harmless general tasks may fall back to `GENERAL_AI`; material actions cannot bypass authority through fallback.

`MAX_ROUTING_HOPS = 2`
`SAME_REQUEST_SAME_OCS_REENTRY = PROHIBITED`
`NO_VALID_SPECIALIST_ROUTE → GENERAL_AI | HOLD`

## 5. OURO / PRATA behavior

### OURO
OURO exposes facts and deterministic projections and may ask PRATA for explanations, summaries or anomaly suggestions. It never depends on inference for truth.

Allowed advisory inference: explain, summarize, compare, detect anomaly, suggest next action.

`INFERENCE → CANONICAL_STATE_WRITE = PROHIBITED`

### PRATA
PRATA is the first-class intelligence layer: general assistance, OCS specialist reasoning, cross-OCS routing, tool/source retrieval, recommendations, automation preparation and provider/model invocation when capability is materially available.

PRATA may propose but cannot self-grant authority or promotion.

## 6. Diagnostic instrumentation

The earlier speech-to-text reference to “métrica” was not the requested top-level artifact; the requested artifact is this metaarquitetura. Diagnostic metrics remain subordinate instrumentation only.

Every diagnostic metric record carries `SOURCE_REF`, `MEASUREMENT_METHOD`, `MEASUREMENT_VERSION`, `OBSERVED_AT`, `WINDOW`, `COMPLETENESS`, `UNKNOWN_SEMANTICS`.

`NO_SINGLE_METRIC_CAN_PROMOTE`
`NO_SINGLE_METRIC_CAN_CLOSE_QUALITY_GATE`
`NO_METRIC_CAN_OVERRIDE_EVIDENCE`
`NO_METRIC_CAN_SUPPRESS_REQUIRED_ESCALATION`

Safety diagnostics include: OURO availability under PRATA failure, routing loops/hops, authority bypass, direct inference writes, self-promotion, missing receipts, inference/fact confusion and source-access/model-invocation conflation.

## 7. Pipeline

```text
B10-AR0 RECOVER + FREEZE BASELINE
→ B10-AR1 METAARCHITECTURE + LEGACY BASELINE RECONCILIATION
→ B10-AR2 PRODUCT / INFORMATION ARCHITECTURE
→ B10-AR3 OURO / PRATA MODULE CONTRACT
→ B10-AR4 OCS INFERENCE FABRIC
→ B10-AR5 TOOL + HOST / PROVIDER CAPABILITY BOUNDARY
→ B10-AR6 BOUNDED CONTROL + FRONTEND EVOLUTION
→ B10-AR7 OBSERVABILITY / DIAGNOSTIC INSTRUMENTATION
→ B10-AR8 E2E / NEGATIVE / IDEMPOTENCY / RECOVERY
→ B10-AR9 UX + ACCESSIBILITY ASSESSMENT
→ B10-AR10 EXACT-HEAD FREEZE
→ B10-AR11 ADVERSARIAL / FEDERATED ASSURANCE
→ PROMOTION READINESS
→ FOUNDER APPROVAL
```

## 8. Action plan

1. Preserve IB6/current Command projections and the historical OBSERVAR branch unchanged.
2. Reuse the old single-file responsive frontend as the presentation seed.
3. Replace obsolete cookie/session and old `/command/*` assumptions with current bearer/org/cockpit contracts.
4. Preserve summary-first, private Founder experience, provenance awareness and mobile responsiveness.
5. Add aggregate cockpit without new persistence.
6. Add ten-OCS view and identity boundary.
7. Add CUPUWA-inspired OURO/PRATA experience.
8. Add shared OCS inference planning policy, general fallback and anti-loop routing.
9. Require actual tool/source capability for retrieval and actual provider adapter evidence for live model invocation.
10. Keep material actions authority-gated.
11. Run negative tests for authority bypass, invalid OCS, loops and PRATA isolation.
12. Run Command, governance, Chat Runtime, Execution Plane, Hazel and StateCore regressions.
13. Run frontend/interaction/accessibility assessment.
14. Freeze exact HEAD and run independent adversarial/federated assurance.
15. Founder approval remains an explicit reserved act.

## 9. Gate architecture

The current REIS OS gate grammar remains canonical; B10 creates no parallel macro-gate system.

```text
G0 — EXECUTION GATE
G1 — TECHNICAL QUALITY GATE
G2 — INDEPENDENT ASSURANCE GATE (CONDITIONAL / POLICY-BOUND)
G3 — PROMOTION READINESS GATE
G4 — FOUNDER APPROVAL GATE
```

B10-specific assessments inside that grammar:
- `A-B10-BASELINE` — exact base/readback, legacy baseline provenance, no parallel SoR.
- `A-B10-PROJECTION` — cockpit composes existing sources; UNKNOWN stays UNKNOWN.
- `A-B10-OURO-PRATA` — PRATA failure does not break OURO; inference creates no canonical truth.
- `A-B10-INFERENCE` — response modes, invalid OCS and anti-loop behavior bounded.
- `A-B10-CAPABILITY` — source access and model invocation distinct; unavailable capability not fabricated.
- `A-B10-AUTHORITY` — preparation cannot bypass authority/promotion/receipt/readback.
- `A-B10-FRONTEND` — evolved legacy baseline is served, mobile-responsive and aligned with current contracts.
- `A-B10-E2E` — regressions, isolation, idempotency, fencing and recovery.
- `A-B10-UX` — Founder-critical flows, accessibility and epistemic clarity.

Every material assessment declares evidence, verifier, verdict and routing. No receipt means no accepted state transition.

## 10. Delivery agenda

### Metaarquitetura / arquitetura
1. current architectural state;
2. baseline lineage and reused/replaced pieces;
3. closed/open components;
4. active gate + assessments;
5. material conflicts/evidence;
6. readiness + next action.

### Operational
1. repository / exact HEAD;
2. implementation delta;
3. frontend/backend integration state;
4. tests / CI;
5. blockers / reservations;
6. assurance / next action.

### Founder
1. where are we?;
2. what was proven?;
3. what remains a reservation?;
4. who owns the next assessment/gate?;
5. is Founder action required?;
6. what happens next?

## 11. Source-of-truth boundary

- code / technical provenance: GitHub;
- visual specification: Figma when explicitly designated;
- institutional mission/identity/authority: existing REIS OS canonical stores/contracts;
- Kernel: runtime authority boundary;
- Hazel: continuity/recovery;
- Execution Plane: bounded execution ledger;
- governance candidate store: governance/evidence overlay;
- Command: projection + bounded control surface;
- OCS inference fabric: cognitive/planning capability, not canonical persistence.

No direct UI, model or inference output becomes institutional truth without the existing execution/authority/evidence path.

## 12. Frontend baseline decision

The previous `FRONTEND_PRODUCT_EXPERIENCE = NOT_YET_PROVEN` statement was superseded by source discovery.

Material evidence now establishes:
- historical branch `feature/reis-os-command-v0.1-observar` still exists;
- `app/command/frontend/index.html` is a real responsive private Command UI baseline;
- the historical app served it through `/` and `/command-ui`;
- the historical presentation tests enforced read-only/provenance behavior.

Decision:

```text
OLD_COMMAND_FRONTEND = PRESERVED_AS_HISTORICAL_BASELINE
OLD_BRANCH_MUTATION = FALSE
B10_FRONTEND_STRATEGY = REUSE_AND_EVOLVE
NEW_FRONTEND_STACK = NOT_REQUIRED_AT_THIS_STAGE
```

The B10 branch now carries an evolved copy at the same logical path, adapted to current auth/organization contracts, `/v1/command/cockpit`, OURO/PRATA and OCS/AI planning. This is an evolutionary delta, not a rewrite.

`LIVE_PROVIDER_MODEL_INFERENCE = NOT_YET_PROVEN`
`FRONTEND_IMPLEMENTATION = MATERIALIZED_CANDIDATE`
`UX_ACCESSIBILITY_ASSURANCE = PENDING`
