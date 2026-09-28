# IRIS-COMMAND-EXPERIENCE-ACCEPTANCE-MATRIX-001

## Purpose
Convert the Nóesis-prepared Command UX/UI foundation into an explicit Íris validation and consolidation package.

This document does not approve final UX. It defines what Íris must verify, refine, accept, or return with findings.

## Input baseline

Use these candidate inputs from PR #68:
- `COMMAND-FOUNDER-EXPERIENCE-ARCHITECTURE-001`
- `COMMAND-HOME-FOUNDER-COCKPIT-001`
- `COMMAND-ATLAS-MOBILE-INTERACTION-001`
- `COMMAND-DESIGN-TOKENS-SEMANTIC-CONTRACT-001`
- `COMMAND-CORE-COMPONENT-ANATOMY-001`
- `COMMAND-HIGH-FIDELITY-WIREFRAME-SPEC-001`
- Lyra brand package when returned.

## Frozen UX constraints

Íris must preserve:

```text
SITUAÇÃO → ATENÇÃO → OBJETO → EVIDÊNCIA
STATE → CONTEXT → EVIDENCE → AVAILABLE_ACTIONS
ASK != COMMAND
CAN_DO != MAY_DO
REQUESTED != EXECUTED
PROPOSED != AUTHORIZED
EXECUTED != VERIFIED
VERIFIED != ASSURED
UI_DOES_NOT_CREATE_AUTHORITY
COLOR_ONLY_MEANING = PROHIBITED
```

## Acceptance matrix

| Area | Candidate baseline | Íris must verify | PASS condition |
|---|---|---|---|
| Home | Situação / Mudanças / Atenção / Bloqueios / Decisões | hierarchy + scanability | Founder understands current state without opening detail |
| Navigation | Início / Operações / OCS / Evolução / Conversa | mobile fit + information scent | primary destinations remain clear with one-hand use |
| State-first UX | state before action | all critical flows | no operational CTA precedes state/authority context |
| Mission detail | lifecycle + evidence + responsible OCS | causal readability | state transitions and blockers understandable without inference |
| OCS detail | identity + mission + capability/authority + instance + recovery | density + hierarchy | capability never visually collapses into authority |
| Evidence | evidence refs + freshness + validity state | discovery speed | material evidence reachable within <=2 drill-downs from a claim |
| Assurance | separate assurance status | distinction from verification | VERIFIED and ASSURED are never visually synonymous |
| Recovery | generation + predecessor + checkpoint/recovery | recoverability comprehension | Founder can understand current vs predecessor/recovered state |
| Atlas | organism → OCS → component → relation → evidence | graph navigation + context persistence | drill-down never loses object identity or layer context |
| Atlas layers | structural/functional/causal/authority/observability/recovery/assurance | semantics + filter clarity | visible relation never implies proven causality |
| Graph inspector | identity/state/freshness/function/relations/authority/evidence/history | completeness + progressive disclosure | compact enough for mobile, complete enough for investigation |
| Unknown/stale/conflict | explicit semantic states | all screens | UNKNOWN != ZERO and STALE != CURRENT remain perceptible in compact mode |
| Accessibility | label + non-color channel | screen reader, contrast, text scale, touch | critical meaning survives color blindness, text scaling and no-motion modes |
| Data density | high-information but structured | mobile scanning | density does not become ambiguity |
| Conversation | cognitive surface | authority separation | user cannot mistake conversation suggestion for executed command |

## Golden paths to validate

### GP-01 — Founder current-state read
```text
Open Command
→ read current situation
→ identify attention
→ inspect blocker
→ open evidence
→ understand whether Founder decision is actually required
```

### GP-02 — OCS inspection
```text
Home/OCS
→ select OCS
→ read identity + mission state
→ inspect current instance/generation
→ inspect authority boundary
→ open evidence/recovery if needed
```

### GP-03 — Atlas investigation
```text
Atlas overview
→ choose semantic layer
→ focus OCS
→ select component/relation
→ open inspector
→ inspect state/freshness/evidence
→ return without losing context
```

### GP-04 — Epistemic hold
```text
Attention/HOLD
→ identify hold class
→ inspect why
→ inspect evidence sufficiency
→ distinguish NOT_PROVEN vs FAIL vs NOT_AUTHORIZED
```

### GP-05 — Founder decision
```text
Decision queue
→ inspect object
→ inspect evidence + assurance + authority source
→ understand requested decision
→ no action surface is considered implementation authority until separately authorized
```

## Required Figma-ready frames

Íris should consolidate at minimum:

```text
M01_HOME_DEFAULT
M02_HOME_HOLD
M03_HOME_STALE_DATA
M04_OCS_DETAIL_ACTIVE
M05_OCS_DETAIL_RECOVERY
M06_OCS_DETAIL_CONFLICT
M07_ATLAS_OVERVIEW
M08_ATLAS_OCS_FOCUS
M09_ATLAS_OBJECT_INSPECTOR
M10_ATLAS_NOT_PROVEN
M11_DECISION_QUEUE
M12_EVIDENCE_DETAIL
M13_ASSURANCE_DETAIL
M14_RECOVERY_CENTER
```

## Component acceptance

Íris must decide for each candidate component:

```text
KEEP
REFINE
SPLIT
MERGE
REMOVE
DEFER_WITH_REASON
```

Components:
- AppShell
- TopContextBar
- BottomNavigation
- SituationSummary
- AttentionCard
- GateStateCard
- MissionCard
- OCSCard
- StateBadge
- FreshnessBadge
- EvidenceBadge
- AuthorityBoundary
- Timeline
- EvidenceList
- DecisionQueue
- MetricCard
- TrendPanel
- GraphCanvas
- GraphLayerSelector
- GraphInspector
- FilterSheet
- RecoveryPanel
- AssurancePanel
- EmptyState
- LoadingState
- ConflictState
- ErrorState

## Accessibility evidence expected

Íris should return evidence or explicit review notes for:
- contrast of every epistemic state combination;
- text scaling at large Android accessibility sizes;
- screen-reader labeling of state + object + freshness;
- graph textual fallback;
- no hover-only interaction;
- minimum touch targets;
- reduced-motion behavior;
- color-independent state interpretation.

## Dependency on Lyra

Íris may proceed with structure before Lyra closes brand, but final visual consolidation must explicitly reconcile Lyra's returned:
- color system;
- typography;
- OCS identity strategy;
- iconography;
- voice/tone rules.

If Lyra changes semantic visual treatment, Íris must update tokens/components without weakening UX invariants.

## Stop conditions

Íris must return HOLD if:
- visual hierarchy creates false authority;
- evidence becomes hard to reach;
- graph density destroys causal/structural legibility;
- Android compact mode hides critical state labels;
- accessibility conflicts cannot be repaired within the candidate system;
- brand decisions make epistemic states ambiguous.

## Exit state

```text
IRIS_UX_REVIEW = PASS_CANDIDATE | PASS_WITH_REVISIONS | HOLD
FIGMA_READY = TRUE only after required frames and accessibility checks are materially represented
FINAL_UX_FREEZE = FALSE unless explicitly promoted later
```

No output from this matrix authorizes production UI implementation.